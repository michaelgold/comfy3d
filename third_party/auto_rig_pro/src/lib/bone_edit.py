import bpy
from math import *
from mathutils import *
from .maths_geo import *
from .collections import *
from .. import auto_rig_datas as ard

def init_bone_coordinates(edit_bone):
    edit_bone.head = [0,0,0]
    edit_bone.tail = [0,0,0.1]


def is_deforming(bone):
    if get_edit_bone(bone):
        return get_edit_bone(bone).use_deform
        

def get_selected_edit_bones():
    return bpy.context.selected_editable_bones


def get_edit_bone(name):    
    return bpy.context.object.data.edit_bones.get(name)


def move_bone_to_bone(bone1, bone2):
    # move editbone bone1 to bone2 based on the head location
    vec_delta = bone2.head - bone1.head
    roll = bone1.roll
    bone1.head += vec_delta
    bone1.tail += vec_delta
    bone1.roll = roll


def move_bone(bone, value, axis):
    get_edit_bone(bone).head[axis] += value / bpy.context.scene.unit_settings.scale_length
    get_edit_bone(bone).tail[axis] += value / bpy.context.scene.unit_settings.scale_length


def copy_bone_rotation(bone1, bone2):
    # copy editbone bone1 rotation to bone2
    bone1_vec = bone1.tail-bone1.head
    bone2_length = (bone2.tail-bone2.head).magnitude
    bone2.tail = bone2.head + (bone1_vec.normalized() * bone2_length)
    bone2.roll = bone1.roll


def copy_bone_transforms(bone1, bone2):
    # copy editbone bone1 transforms to bone 2
    if bone1 == None or bone2 == None:       
        return
        
    bone2.head = bone1.head.copy()
    bone2.tail = bone1.tail.copy()
    bone2.roll = bone1.roll


def copy_bone_transforms_mirror(bone1, bone2):
    bone01 = get_edit_bone(bone1 + ".l")
    bone02 = get_edit_bone(bone2 + ".l")

    bone02.head = bone01.head
    bone02.tail = bone01.tail
    bone02.roll = bone01.roll

    bone01 = get_edit_bone(bone1 + ".r")
    bone02 = get_edit_bone(bone2 + ".r")

    bone02.head = bone01.head
    bone02.tail = bone01.tail
    bone02.roll = bone01.roll


def rotate_edit_bone(edit_bone, angle_radian, axis):
    old_head = edit_bone.head.copy()
    # rotate
    R = Matrix.Rotation(angle_radian, 4, axis.normalized())
    edit_bone.transform(R, roll=True)
    # back to initial head pos
    offset_vec = -(edit_bone.head - old_head)
    new_x_axis = edit_bone.x_axis.copy()
    edit_bone.head += offset_vec
    edit_bone.tail += offset_vec
    # preserve roll
    align_bone_x_axis(edit_bone, new_x_axis)


def create_edit_bone(bone_name, deform=False, tag=None):
    _b = bpy.context.active_object.data.edit_bones.get(bone_name)
    if _b == None:
        _b = bpy.context.active_object.data.edit_bones.new(bone_name)
        _b.use_deform = deform
        _b.head = Vector((0.0,0.0,0.0))
        _b.tail = Vector((0.0,0.0,0.1))
        #init_bone_coordinates(_b)
        
    if tag:# optional tag as custom prop
        _b[tag] = 1
        
    return _b


def select_edit_bone(_name, mode=1):
    _o = bpy.context.active_object
    _ebone = get_edit_bone(_name)

    if mode == 1:
        _o.data.bones.active = _o.pose.bones[_name].bone
    elif mode == 2:
        _o.data.edit_bones.active = _o.data.edit_bones[_name]
        _o.data.edit_bones.active.select = True

    _ebone.select_head = True
    _ebone.select_tail = True
    _ebone.select = True


def delete_edit_bone(editbone):
    bpy.context.active_object.data.edit_bones.remove(editbone)
    
    
def mirror_bones_transforms(ebones_list):
    roll_copy = {}
    for ebone in ebones_list:
        roll_copy[ebone.name] = ebone.roll                

    # mirror head-tails
    for ebone in ebones_list:
        ebone.head[0] *= -1
        
        # use_connect handling
        found_connected_child = False
        if len(ebone.children):  
            for ch in ebone.children:
                if ch.use_connect:
                    found_connected_child = True
                    break
        
        if not found_connected_child:
            ebone.tail[0] *= -1
            
    # mirror roll
    for ebone in ebones_list:
        ebone.roll = -roll_copy[ebone.name]