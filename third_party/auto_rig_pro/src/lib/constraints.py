import bpy
from .bone_pose import *
from mathutils import *
from math import *


def restore_actions_cns_lib(dict):
    for pbname in dict:
        cns_dict = dict[pbname]
        pb = get_pose_bone(pbname)
        for cns_name in cns_dict:
            lib_action_name = cns_dict[cns_name]
            lib_action = None
            for _act in bpy.data.actions:
                if _act.name == lib_action_name and _act.library:
                    lib_action = _act
                    break
            
            if lib_action:
                cns = pb.constraints.get(cns_name)
                cns.action = lib_action
                #print("Replace with lib action:", pbname, lib_action_name)


def save_actions_cns_lib():
    actions_cns_lib_dict = {}
    for pb in bpy.context.active_object.pose.bones:
        cnss = {}
        for cns in pb.constraints:
            if cns.type == "ACTION":
                if cns.action and cns.action.library:
                    cnss[cns.name] = cns.action.name
        actions_cns_lib_dict[pb.name] = cnss
        
    return actions_cns_lib_dict
    


def enable_constraint(cns, value):
    if bpy.app.version >= (3,0,0):
        cns.enabled = value
    else:
        cns.mute = not value     
        
        
def set_constraint_inverse_matrix(cns):
    # set the inverse matrix of Child Of constraint
    subtarget_pbone = get_pose_bone(cns.subtarget)
    if subtarget_pbone:
        cns.inverse_matrix = subtarget_pbone.bone.matrix_local.to_4x4().inverted()


def add_copy_transf(p_bone, tar=None, subtar='', h_t=0.0, no_scale=False):
    if tar == None:
        tar = bpy.context.active_object

    if no_scale:
        cns1 = p_bone.constraints.new("COPY_LOCATION")
        cns1.name = "Copy Location"
        cns1.target = tar
        cns1.subtarget = subtar
        cns1.head_tail = h_t

        cns2 = p_bone.constraints.new("COPY_ROTATION")
        cns2.name = "Copy Rotation"
        cns2.target = tar
        cns2.subtarget = subtar

        return cns1, cns2
    else:
        cns1 = p_bone.constraints.new("COPY_TRANSFORMS")
        cns1.name = "Copy Transforms"
        cns1.target = tar
        cns1.subtarget = subtar
        cns1.head_tail=h_t

        return cns1, None
        
        
def get_constraint_index(pb, cns):
    for i, c in enumerate(pb.constraints):
        if c == cns:
            return i        

        
def move_constraint(pbone, cns, dir, repeat):
    # must be in pose mode    
    armature = bpy.context.active_object
    
    # the bone layer must be visible
    enabled_layers = []    
    
    if bpy.app.version >= (4,0,0):
        for collec in armature.data.collections:
            if is_bone_in_layer(pbone.name, collec.name):
                if collec.is_visible == False:
                    collec.is_visible = True
                    enabled_layers.append(collec.name)
    else:
        for i, lay in enumerate(pbone.bone.layers):
            if lay and armature.data.layers[i] == False:
                armature.data.layers[i] = True
                enabled_layers.append(i)
 
    # move
    if bpy.app.version >= (2, 81, 16):        
        cns_idx = get_constraint_index(pbone, cns)
        #print('cns_idx', cns_idx)
        #print('repeat', repeat)
        to_idx = cns_idx+repeat if dir == 'DOWN' else cns_idx-repeat 
        if to_idx > len(pbone.constraints)-1:
            to_idx = len(pbone.constraints)-1
        if to_idx < 0:
            to_idx = 0
        pbone.constraints.move(cns_idx, to_idx)
        
    else:# backward-compatibility
        bpy.context.active_object.data.bones.active = pbone.bone
        my_context = bpy.context.copy()
        my_context["constraint"] = cns

        for i in range(0, repeat):
            if dir == 'UP':
                bpy.ops.constraint.move_up(my_context, constraint=cns.name, owner='BONE')
            elif dir == 'DOWN':
                bpy.ops.constraint.move_down(my_context, constraint=cns.name, owner='BONE')

    # restore layers
    for idx in enabled_layers:
        if bpy.app.version >= (4,0,0):
            armature.data.collections.get(idx).is_visible = False
        else:
            armature.data.layers[idx] = False