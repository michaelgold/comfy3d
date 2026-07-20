import bpy
import addon_utils
from bpy_extras import anim_utils
from .. import auto_rig_datas as ard
from .collections import *
from .armature import *

class ARP_blender_version:
    _string = bpy.app.version_string
    blender_v = bpy.app.version
    _float = 0.0
    
    def __init__(self):
        str = ''.join([i for i in self._string if i in '0123456789'])#int(_string.replace('.', ''))#blender_v[0]*100+blender_v[1]+blender_v[2]*0.01
        self._float = float(str)
        if len(str) > 3:# hu! some version are defined as '3.00', some as '2.93.9'
            self._float = float(str)/10
        
blender_version = ARP_blender_version()


def is_pbone_selected(pb):
    if bpy.app.version >= (5,0,0):
        return pb.select
    else: return pb.bone.select
        

def select_pb_db(pbone, state=True):
    if bpy.app.version >= (5,0,0):
        pbone.select = state
    else: pbone.bone.select = state
        

def is_proxy(obj):
    # proxy atttribute removed in Blender 3.3
    if 'proxy' in dir(obj):
        if obj.proxy:
            return True
    return False


def get_autorigpro_version():

    addons = None
    if bpy.app.version >= (4,2,0):
        addons = addon_utils.modules()
    else:
        addons = addon_utils.modules()[:]
    
    for addon in addons:    
        addon_name = addon.__name__ if bpy.app.version >= (4,2,0) else addon.bl_info['name']   
        arp_name = 'bl_ext.user_default.auto_rig_pro' if bpy.app.version >= (4,2,0) else 'Auto-Rig Pro'
        quickr_name = '_quick_rig' if bpy.app.version >= (4,2,0) else 'Quick Rig' 
        if addon_name.startswith(arp_name) and not quickr_name in addon_name:
            #print(addon)
            #print()
            ver_list = addon.bl_info.get('version')
            ver_string = str(ver_list[0]) + str(ver_list[1]) + str(ver_list[2])
            ver_int = int(ver_string)
            return ver_int
            
            
def ver_int_to_str(version_int):
    to_str = str(version_int)
    return to_str[0] + '.' + to_str[1] + to_str[2] + '.' + to_str[3] + to_str[4]


def convert_drivers_cs_to_xyz(armature):
    # Blender 3.0 requires Vector3 custom_shape_scale values
    # convert single uniform driver to vector3 array drivers
    drivers_armature = [i for i in armature.animation_data.drivers]   
    
    for dr in drivers_armature:
        if 'custom_shape_scale' in dr.data_path:
            if not 'custom_shape_scale_xyz' in dr.data_path:                      
                for i in range(0, 3):
                    new_dr = armature.animation_data.drivers.from_existing(src_driver=dr)
                    new_dr.data_path = new_dr.data_path.replace('custom_shape_scale', 'custom_shape_scale_xyz')
                    new_dr.array_index = i
                    new_dr.driver.expression += ''# update hack

                armature.driver_remove(dr.data_path, dr.array_index)                
                
    # tag in prop
    armature.data["arp_updated_3.0"] = True
    #print("Converted custom shape scale drivers to xyz")
    
 
def convert_armature_layers_to_collection(armature):
    # convert old armature layers and bone colors groups
    # from pre Blender 4.0 versions, to collections
    
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.transform.translate(value=(0, 0, 0))# update hack
    bpy.context.evaluated_depsgraph_get().update()
    
    get_armature_collections(armature).update()
    
    col_names = [col.name for col in get_armature_collections(armature)]# make a copy of current collections, necessary for proper removal
    
    for col_name in col_names:#armature.data.collections_all:
        _col = get_armature_collections(armature).get(col_name)
        if _col == None:# debug...
            #print(" Collec is None, error when removing collection! Exit")
            continue

        # remove deprecated bones color groups
        if _col.name in ard.bones_groups_to_remove:
            armature.data.collections.remove(_col)
            continue
            
        # rename color collections
        if _col.name in ard.bones_groups:
            _col.name = 'color_'+_col.name
        
    # rename bones collections
    #print('Rename collections...')
    
    get_armature_collections(armature).update()
    
    for i, _col in enumerate(get_armature_collections(armature)):
        if _col == None:#Debug, for some reasons Mac throws a None collection when appending the Bird armature
            continue
        if _col.name.startswith('Layer '):
            lidx = int(_col.name.split(' ')[1])-1
            
            # special case, both kilt bones and feather bones are in layer 24
            # Split in two dedicated collections
            if lidx == 24:
                for bone in armature.data.bones:
                    if is_bone_in_layer(bone.name, _col.name):
                        if 'arp_kilt' in bone.keys():
                            set_bone_layer(bone, 'mch_kilt_masters')
                        if 'feather' in bone.name:
                            set_bone_layer(bone, 'mch_feathers')
                   
                # remove layer 24
                # in case other unexpected bones remain in layer 24, move them out first
                for bone in armature.data.bones:
                    if is_bone_in_layer(bone.name, _col.name):
                        set_bone_layer(bone, 'Misc')
                continue
                
            for col_name in ard.layer_col_map:
                if ard.layer_col_map[col_name] == lidx:
                    _col.name = col_name
                    break
                    
    # remove remaining Layer 24 if any
    col_24 = get_armature_collections(armature).get('Layer 25')
    if col_24:
        armature.data.collections.remove(col_24)

    # ensure all ARP collections are created
    for col_name in ard.layer_col_map:
        if col_name[0].isupper():# only main collections with capital letters                
            if get_armature_collections(armature).get(col_name) == None:
                #print('Create collection', col_name)
                armature.data.collections.new(col_name)
            
    sort_armature_collections(armature)    
    
    # update tag as prop
    armature.data["arp_updated_4.0"] = True
    

def convert_picker_layers_to_collection(armature):
    converted = False
    for pb in armature.pose.bones:
        if 'layer' in pb.keys() and not 'collec' in pb.keys():
            layer_idx = pb['layer']
            layer_name = None
            
            for col_name in ard.layer_col_map:
                if ard.layer_col_map[col_name] == layer_idx:
                    layer_name = col_name
                    break
            pb['collec'] = col_name
            converted = True
    return converted
    

def is_fc_bb_param(fc, param):    
    # is the fcurve a bendy-bones parameter?
    # bendy-bones params data path depends on the Blender version
    
    # scale are array
    #   scale in
    if param == 'bbone_scaleinx':       
        if get_bbone_param_name(param) in fc.data_path:
            if (bpy.app.version >= (3,0,0) and fc.array_index == 0) or (bpy.app.version < (3,0,0)):
                return True
    elif param == 'bbone_scaleiny':     
        if get_bbone_param_name(param) in fc.data_path:
            if (bpy.app.version >= (3,0,0) and fc.array_index == 1) or (bpy.app.version < (3,0,0)):
                return True
    elif param == 'bbone_scaleinz': 
        if 'bbone_scalein' in fc.data_path:# only in Blender 3.0 and after
            if (bpy.app.version >= (3,0,0) and fc.array_index == 2):
                return True
        
    #   scale out
    elif param == 'bbone_scaleoutx':    
        if get_bbone_param_name(param) in fc.data_path:
            if (bpy.app.version >= (3,0,0) and fc.array_index == 0) or (bpy.app.version < (3,0,0)):
                return True
    elif param == 'bbone_scaleouty':    
        if get_bbone_param_name(param) in fc.data_path:
            if (bpy.app.version >= (3,0,0) and fc.array_index == 1) or (bpy.app.version < (3,0,0)):
                return True
    elif param == 'bbone_scaleoutz':
        if 'bbone_scaleout' in fc.data_path:# only in Blender 3.0 and after
            if (bpy.app.version >= (3,0,0) and fc.array_index == 2):
                return True


def get_bbone_param_name(setting):
    # bendy-bones setting name depending on the Blender version   
    # curve out
    if setting == 'bbone_curveoutz':
        if bpy.app.version < (3,0,0):
            return 'bbone_curveouty'
        else:
            return 'bbone_curveoutz'
    # curve in
    elif setting == 'bbone_curveinz':
        if bpy.app.version < (3,0,0):
            return 'bbone_curveiny'
        else:
            return 'bbone_curveinz'
            
    # scale in X
    elif setting == 'bbone_scaleinx':
        if bpy.app.version < (3,0,0):
            return 'bbone_scaleinx'
        else:
            return 'bbone_scalein'
    # scale in Y
    elif setting == 'bbone_scaleiny':
        if bpy.app.version < (3,0,0):
            return 'bbone_scaleiny'
        else:
            return 'bbone_scalein'
            
    # scale out X
    elif setting == 'bbone_scaleoutx':
        if bpy.app.version < (3,0,0):
            return 'bbone_scaleoutx'
        else:
            return 'bbone_scaleout'
    # scale in Y
    elif setting == 'bbone_scaleouty':
        if bpy.app.version < (3,0,0):
            return 'bbone_scaleouty'
        else:
            return 'bbone_scaleout' 


def check_id_root(action):    
    if bpy.app.version >= (2,90,1):        
        if getattr(action, 'id_root', None) == 'OBJECT':
            return True
        elif getattr(action, 'id_root', None) == 'KEY':# shape keys actions are not exportable armature actions in that case
            return False
        else:# sometimes, no tag, not sure why. Keep it then
            return True
    else:
        return True
        
        
def invert_angle_with_blender_versions(angle=None, bone=False, axis=None):
    # Deprecated!
    # Use rotate_edit_bone() and rotate_object() instead
    #
    # bpy.ops.transform.rotate has inverted angle value depending on the Blender version
    # this function is necessary to support these version specificities
  
    invert = False
    if bone == False:
        if (bpy.app.version >= (2,83,0) and bpy.app.version < (2,90,0)) or (bpy.app.version >= (2,90,1) and bpy.app.version < (2,90,2)):
            invert = True

    elif bone == True:
        # bone rotation support
        # the rotation direction is inverted in Blender 2.83 only for Z axis
        if axis == "Z":
            if bpy.app.version >= (2,83,0) and bpy.app.version < (2,90,0):
                invert = True
        # the rotation direction is inverted for all but Z axis in Blender 2.90 and higher
        if axis != "Z":
            if bpy.app.version >= (2,90,0):
                invert = True

    if invert:
        angle = -angle

    return angle

          
def disable_bone_inherit_scale(editbone):
    if bpy.app.version >= (2,81,0):
        editbone.inherit_scale = 'NONE'
    else:# backward-compatibility
        editbone.use_inherit_scale = False
        
        
def enable_bone_inherit_scale(editbone):
    if bpy.app.version >= (2,81,0):
        editbone.inherit_scale = 'FULL'
    else:# backward-compatibility
        editbone.use_inherit_scale = True
        
        
def find_fcurve(act, dp, slot_idx=0, slot_name=None, fc_index=0):
    # find fcurve from action
    # use slots in Blender 4.4+
    
    if bpy.app.version >= (4,4,0):
        # check for missing slots
        if len(act.slots) == 0:
            #print("Warning, this action has not slots:", act.name)
            if bpy.app.version < (5,0,0):
                return find_fcurve_legacy(act, dp, fc_index)
            else:
                return None
            
        # check for missing channel bag
        cb = None
        try: cb = anim_utils.action_get_channelbag_for_slot(act, act.slots[slot_idx if slot_name == None else slot_name])
        except: print('no channel bag found on action', act.name, 'slot', slot_name if slot_name != None else slot_idx)
        if cb == None:
            if bpy.app.version < (5,0,0):
                return find_fcurve_legacy(act, dp, fc_index)
            else:
                return None
        
        # get fcurve from action slot
        return cb.fcurves.find(dp, index=fc_index)
    
    # fallback
    return find_fcurve_legacy(act, dp, fc_index)
    
    
def find_fcurve_legacy(act, dp, fc_index):
    # only Blender < (5,0,0)
    return act.fcurves.find(data_path=dp, index=fc_index)
        
        
def create_fcurve(act, dp, slot_idx=0, fc_index=0, action_group=''):
    if bpy.app.version >= (5,0,0):        
        if len(act.slots) == 0:# buggy action, no slots
            print("Warning, this action has not slots, cannot create fcurve:", act.name)
            return None
        
        cb = anim_utils.action_ensure_channelbag_for_slot(act, act.slots[slot_idx])
        return cb.fcurves.new(dp, index=fc_index, group_name=action_group)
        
    else:
        return act.fcurves.new(dp, index=fc_index, action_group=action_group)
        
        
def delete_fcurve(act, fc, slot_idx=0):
    if bpy.app.version >= (5,0,0):
        cb = anim_utils.action_ensure_channelbag_for_slot(act, act.slots[slot_idx])
        cb.fcurves.remove(fc)
    else:
        act.fcurves.remove(fc)
        
        
def get_action_fcurves(act, slot_idx=0, as_list=True):
    if bpy.app.version >= (5,0,0):    
        if len(act.slots) == 0:# buggy action, no slots
            print("Warning, this action has not slots, skipped:", act.name)
            return []
            
        cb = anim_utils.action_ensure_channelbag_for_slot(act, act.slots[slot_idx])

        if cb:
            if as_list:
                return [_fc for _fc in cb.fcurves if _fc != None]# check for None curve, debug
            else:
                return cb.fcurves
        else:
            print("No fcurves found in this slot:", slot_idx)
            return []
    else:
        return act.fcurves
        
        
def get_prefs():
    if bpy.app.version >= (4,2,0):
        return bpy.context.preferences.addons[__package__[:-8]].preferences
    else:
        return bpy.context.preferences.addons[__package__.split('.')[0]].preferences