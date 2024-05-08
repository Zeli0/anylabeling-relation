import json
import numpy as np
import cv2 as cv
import pathlib
import os
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QPolygon
from .shape import Shape

# Loads the inputs from json files when prompted into objects
# Check if there are ids given to the objects in the json files - if not, give them ids
# Should bounding boxes be calculated as well?

# Separate class used to package the inputs back into a better format? Or at least provide the proper augmentations to the original json file

class DataHandler():

  def __init__(self) -> None:
    self.filename = None
    self.objs = None
    self.selected_obj = None
    self.selected_children = []
    self.selected_parents = []
    self.merge_list = []
    self.unmerge_masks = []

  def reset_selection(self):
    self.selected_obj = None
    self.selected_parents = []
    self.selected_children = []

  def add_base(self, obj):
    self.selected_obj = obj
    if obj == None:
      return
    self.load_obj_relations()

  def add_child(self, child):
    if child is self.selected_obj or child in self.selected_parents:
      return
    if not child in self.selected_children:
      self.selected_obj.add_children([child])
    else:
      self.selected_obj.remove_children([child])

  def add_parent(self, parent):
    if parent is self.selected_obj or parent in self.selected_children:
      return
    if not parent in self.selected_parents:
      self.selected_obj.add_parents([parent])
    else:
      self.selected_obj.remove_parents([parent])

  def mark_mask_to_add(self, obj):
    if obj in self.selected_children or obj in self.selected_parents or obj in self.merge_list or obj is self.selected_obj:
      return
    if obj in self.merge_list:
      self.merge_list.remove(obj)
    else:
      self.merge_list.append(obj)

  def mark_mask_to_remove(self, mask):
    child_masks = [child.qmasks for child in self.selected_children]
    parent_masks = [parent.qmasks for parent in self.selected_parents]
    off_limit_masks = [*child_masks, *parent_masks]
    if mask in off_limit_masks:
      return
    if mask in self.unmerge_masks:
      self.unmerge_masks.remove(mask)
    elif mask in self.selected_obj.qmasks:
      self.unmerge_masks.append(mask)

  def resolve_mask_edits(self):
    for obj in self.merge_list:
      self.selected_obj.add_mask(obj)
      self.objs.remove(obj)
    for mask in self.unmerge_masks:
      new_obj = self.selected_obj.extract_mask(mask)
      self.objs.append(new_obj)
    self.merge_list = []
    self.unmerge_masks = []
    self.update_ids()
    
  def load_obj_relations(self):
    self.selected_parents = self.selected_obj.parents
    self.selected_children = self.selected_obj.children
    
  def update_obj_children(self):
    self.selected_obj.add_children(self.selected_children)

  def update_obj_parents(self):
    self.selected_obj.add_parents(self.selected_parents)

  def calculate_area(self, qpolygon):
    area = 0
    if qpolygon == None:
      return 0
    for i in range(qpolygon.size()):
        p1 = qpolygon[i]
        p2 = qpolygon[(i + 1) % qpolygon.size()]
        d = p1.x() * p2.y() - p2.x() * p1.y()
        area += d
    return abs(area) / 2

  def find_obj_at_point(self, point):
    # Check which mask the point is within
    found = False
    found_area = None
    found_obj = None
    for obj in self.objs:
      for qmask in obj.qmasks:
        curr_area = QPolygon(qmask)
        if curr_area.containsPoint(point, Qt.FillRule.OddEvenFill):
          if not found or (self.calculate_area(found_area) > self.calculate_area(curr_area)):
            found_obj = obj
            print(f"{obj.label} chosen.")
            found = True
            found_area = curr_area
            break
    return found, found_obj
  
  def find_mask_at_point(self, point):
    # Check which mask the point is within
    found = False
    found_mask = None
    for obj in self.objs:
      for qmask in obj.qmasks:
        curr_area = QPolygon(qmask)
        if curr_area.containsPoint(point, Qt.FillRule.OddEvenFill):
          if not found or (self.calculate_area(QPolygon(found_mask)) > self.calculate_area(curr_area)):
            found = True
            found_mask = qmask
            break
    return found, found_mask
  
  def get_objs_from_file(self, filename):
    self.reset_selection()
    self.filename = filename 
    with open(filename, 'r') as file:
      file_contents = json.load(file)

    if "type" in file_contents.keys():
      if file_contents["type"] == "Relation":
        self.load_from_relformat(file_contents)
      else:
        self.load_from_mergeformat(file_contents)
    else:
      self.load_from_anylabel(file_contents)
    self.reset_selection()


  def update_ids(self):
    for i in range(len(self.objs)):
      obj = self.objs[i]
      obj.id = i
