import bpy
from .. import auto_rig_datas as ard
from .version_arm_collec import *

def remove_bone_from_layer(bone, layer_type):
    if bpy.app.version >= (4,0,0):
        arma = bpy.context.active_object
        col = get_armature_collections(arma).get(layer_type)
        if col:
            if bpy.context.mode == 'EDIT_ARMATURE':
                col.unassign(bone)
            else:
                col.unassign(arma.data.bones[bone.name])
        
    else:
        if layer_type in ard.layer_col_map_special:# layer idx special cases
            layer_idx = ard.layer_col_map_special[layer_type]
        else:
            layer_idx = ard.layer_col_map[layer_type]            
        bone.layers[layer_idx] = False
        
        
def set_bone_layer(bone, layer_type, show_new_layer=False, multi=False):
    if bpy.app.version >= (4,0,0):
        arma = bpy.context.active_object
        col = get_armature_collections(arma).get(layer_type)
        if col == None:# create the collection if necessary
            col = arma.data.collections.new(layer_type)
            col.is_visible = show_new_layer
            col['arp_collec'] = True# custom tag
            
        if bpy.context.mode == 'EDIT_ARMATURE':
            col.assign(bone)
        else:
            col.assign(arma.data.bones[bone.name])
        
        if multi:
            return
            
        for col in get_armature_collections(arma):
            if col.name != layer_type:
                if bpy.context.mode == 'EDIT_ARMATURE':
                    col.unassign(bone)
                else:
                    col.unassign(arma.data.bones[bone.name])
        
    else:
        if layer_type in ard.layer_col_map_special:# layer idx special cases
            layer_idx = ard.layer_col_map_special[layer_type]
        else:# standard layer/collec conversion
            layer_idx = ard.layer_col_map[layer_type]   
            
        bone.layers[layer_idx] = True
        
        if multi:
            return
            
        for i, lay in enumerate(bone.layers):
            if i != layer_idx:
                bone.layers[i] = False
                
                
def is_arp_collec(col):
    if col.name in ard.layer_col_map or col.name in ard.layer_col_map_special or col.name.startswith('color_body.') or col.name.startswith('mch_'):
        return True
                
                
def is_bone_in_layer(bone_name, layer_type):
    if bpy.app.version >= (4,0,0):
        if bpy.context.mode == 'EDIT_ARMATURE':# # in Edit mode, access edit bones only. Prone to error otherwise (bone data not up to date)
            in_collection = [ebone.name for ebone in bpy.context.active_object.data.edit_bones if layer_type in ebone.collections]
            return bone_name in in_collection
        else:
            return layer_type in bpy.context.active_object.data.bones.get(bone_name).collections
    else:
        if layer_type in ard.layer_col_map_special:# layer idx special cases
            layer_idx = ard.layer_col_map_special[layer_type]
        else:# standard ARP layer-collec conversion       
            layer_idx = ard.layer_col_map[layer_type]
            
        if bpy.context.mode == 'EDIT_ARMATURE':# in Edit mode, access edit bones only. Prone to error otherwise (bone data not up to date)
            return bpy.context.active_object.data.edit_bones.get(bone_name).layers[layer_idx]
        else:
            return bpy.context.active_object.data.bones.get(bone_name).layers[layer_idx]
        
        
def is_layer_enabled(layer_type):
    if bpy.app.version >= (4,0,0):
        if layer_type == 'mch_disabled':# only there for backward-compatibility, this collection is no more used
            col = get_armature_collections(bpy.context.active_object.data).get(layer_type)
            if col == None:
                bpy.context.active_object.data.collections.new(mch_disabled)
                
        col = get_armature_collections(bpy.context.active_object).get(layer_type)
        if col:
            return col.is_visible
            
    else:# old layer system
        if layer_type in ard.layer_col_map_special:# layer idx special cases
            layer_idx = ard.layer_col_map_special[layer_type]
        else:
            layer_idx = ard.layer_col_map[layer_type]
        return bpy.context.active_object.data.layers[layer_idx]
        
        
def hide_layer(layer_type):
    if bpy.app.version >= (4,0,0):
        col = get_armature_collections(bpy.context.active_object).get(layer_type)
        col.is_visible = False
    else:
        if layer_type in ard.layer_col_map_special:# layer idx special cases
            layer_idx = ard.layer_col_map_special[layer_type]
        else:
            layer_idx = ard.layer_col_map[layer_type]
        bpy.context.active_object.data.layers[layer_idx] = False
        
        
def enable_layer_exclusive(layer_type, use_solo=False):
    if bpy.app.version >= (4,1,0) and use_solo:
        for col in get_armature_collections(bpy.context.active_object):
            col.is_solo = col.name == layer_type
            if col.name == layer_type:
                col.is_visible = True
        return
    
    if bpy.app.version >= (4,0,0):
        for col in get_armature_collections(bpy.context.active_object):
            # ensure to disable pinned collections (Blender 4.1+)
            if bpy.app.version >= (4,1,0):
                col.is_solo = False
            
            if col.name == layer_type:
                col.is_visible = True
            else:
                col.is_visible = False                
    else:
        if layer_type in ard.layer_col_map_special:# layer idx special cases
            layer_idx = ard.layer_col_map_special[layer_type]
        else:
            layer_idx = ard.layer_col_map[layer_type]
        bpy.context.active_object.data.layers[layer_idx] = True
        for i in range(0, 32):
            if i != layer_idx:
                bpy.context.active_object.data.layers[i] = False
                

def enable_layer(layer_type):
    if bpy.app.version >= (4,0,0):
        col = get_armature_collections(bpy.context.active_object).get(layer_type)
        col.is_visible = True
    else:
        if layer_type in ard.layer_col_map_special:# layer idx special cases
            layer_idx = ard.layer_col_map_special[layer_type]
        else:
            layer_idx = ard.layer_col_map[layer_type]
        bpy.context.active_object.data.layers[layer_idx] = True
        
        
def restore_armature_layers(layers_select):
    if bpy.app.version >= (4,0,0):
        for col_name in layers_select:
            col = get_armature_collections(bpy.context.active_object).get(col_name)
            if col:# may have been renamed or deleted
                if bpy.app.version >= (4,1,0):
                    viz, solo = layers_select[col_name]
                    col.is_visible = viz
                    col.is_solo = solo
                else:
                    col.is_visible = layers_select[col_name]
            
        for col in get_armature_collections(bpy.context.active_object):#disable newly created layers
            if not col.name in layers_select:
                col.is_visible = False
            
    else:
        # must enabling at least one
        bpy.context.active_object.data.layers[layers_select[0]] = True
        # restore the armature layers visibility
        for i in range(0, 32):
            bpy.context.active_object.data.layers[i] = layers_select[i]
        
        
def enable_all_armature_layers():
    # enable all layers/collections
    # and return the list of each layer visibility
    
    if bpy.app.version >= (4,0,0):
        layers_select = {}
        
        for col in get_armature_collections(bpy.context.active_object):
            layers_select[col.name] = col.is_visible
            if bpy.app.version >= (4,1,0):
                layers_select[col.name] = col.is_visible, col.is_solo
                col.is_solo = False
                
            col.is_visible = True
            
            
            
        return layers_select
        
    else:
        layers_select = []
        _layers = bpy.context.active_object.data.layers
        
        for i in range(0, 32):
            layers_select.append(_layers[i])
        for i in range(0, 32):
            bpy.context.active_object.data.layers[i] = True

        return layers_select