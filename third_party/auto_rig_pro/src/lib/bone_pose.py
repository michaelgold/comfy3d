import bpy
from .objects import *
from .version import blender_version
from .types_convert import *
from .armature import *


def get_selected_pose_bones():
    return bpy.context.selected_pose_bones


def get_pose_bone(name):
    return bpy.context.active_object.pose.bones.get(name)   

	
def get_custom_shape_scale_prop_name():  
    if bpy.app.version >= (3,0,0):
        return 'custom_shape_scale_xyz'
    else:
        return 'custom_shape_scale'
        
    
def set_custom_shape_scale(pbone, scale):   
    if bpy.app.version >= (3,0,0):
        # uniform scale
        if type(scale) == int or type(scale) == float:
            for i in range(0,3):
                pbone.custom_shape_scale_xyz[i] = scale
        # array scale
        else:
            pbone.custom_shape_scale_xyz = scale
    # pre-Blender 3.0
    else:
        pbone.custom_shape_scale = scale
            

def scale_custom_shape(custom_shape, scale, origin='cog', copy=True):
    # scale the custom shape vertices and return the object
    
    if copy:
        cs_base_name = custom_shape.name
        cs_scaled_name = cs_base_name+'_scaled_'+str(scale)
        cs_base_scaled = get_object(cs_scaled_name)    

        if cs_base_scaled:# if the scaled copy already exists, skip
            return cs_base_scaled
                
        # make
        cs_base_scaled = duplicate_object(new_name=cs_scaled_name, method='data', obj=custom_shape)
        cs_base_scaled.data.name = cs_scaled_name
    else:
        cs_base_scaled = custom_shape
        
    # get centroid
    cog = Vector((0.0,0.0,0.0))    
    if origin == 'cog':
        for v in cs_base_scaled.data.vertices:
            cog += v.co
        cog = cog/len(cs_base_scaled.data.vertices)
    elif origin == 'zero':
        cog = Vector((0.0,0.0,0.0))
        
    # scale verts
    for v in cs_base_scaled.data.vertices:
        scale_vec = cog - v.co
        v.co = v.co + (scale_vec * (1-scale))
        
    return cs_base_scaled
            
            
def get_custom_shape_scale(pbone, uniform=True, as_list=False):
    # returns the custom shape scale setting values
    
    if bpy.app.version >= (3,0,0):
        if uniform:       
            # uniform scale
            val = 0
            for i in range(0,3):
                val += pbone.custom_shape_scale_xyz[i]
            return val/3     
        # array scale
        else:
            if as_list:
                return vector_to_list(pbone.custom_shape_scale_xyz)
            else:
                return pbone.custom_shape_scale_xyz
    # pre-Blender 3.0
    else:        
        return pbone.custom_shape_scale
        
        
def get_custom_shape_translation(pbone, as_list=False):
    if bpy.app.version >= (3,0,0):
        if as_list:
            return vector_to_list(pbone.custom_shape_translation)
        else:
            return pbone.custom_shape_translation
    else:
        return [0,0,0]
        
        
def get_custom_shape_rotation(pbone, as_list=False):
    if bpy.app.version >= (3,0,0):
        if as_list:
            return vector_to_list(pbone.custom_shape_rotation_euler)
        else:
            return pbone.custom_shape_rotation_euler
    else:
        return [0,0,0]
		
		
def set_bone_custom_shape(pbone, cs_name):
    # set the bone custom shape object
    # append first the object from the master file if not present in current file
    
    _sel_rig = bpy.context.active_object
    cs = None
    
    # is the custom shape already there?
    for _o in bpy.data.objects:
        if _o.name.split('.')[0] == cs_name:# support multiple rigs per file, duplicate shapes
            if _o.parent:
                if _o.parent.parent:
                    if _o.parent.parent == _sel_rig.parent:# parented to the active rig's char_grp empty
                        cs = _o
                        break
    
    if cs == None:
        # load custom shape
        append_from_arp(nodes=[cs_name], type='object')
        cs = get_object(cs_name)
        
        
    elif len(cs.users_collection) == 0:
        # custom shape is found, but not in any collection. Fix it
        cs_grp = None
        for __o in bpy.context.scene.objects:
            if __o.name.startswith('cs_grp') and __o.type == 'EMPTY' and __o.parent == _sel_rig.parent:
                cs_grp = __o
                break
        if cs_grp:
            for col in cs_grp.users_collection:            
                col.objects.link(cs)

    # assign custom shape
    pbone.custom_shape = cs
    
    
def set_bone_custom_shape_rot(pbone, rot_angle, axis):
    if bpy.app.version >= (3,0,0):
        axis_int = 0
        if axis == 'Y':
            axis_int = 1
        elif axis == 'Z':
            axis_int = 2
        pbone.custom_shape_rotation_euler[axis_int] = rot_angle
    else:# no custom shape rot setting in older versions
        return


def set_bone_color_group(obj, bone_data, grp_name, custom_color=None, custom_highlight=None, assign_only_if_empty=False, body_side=None):
    
    grp_color = (0.5,0.5,0.5)# default color
    color_collec = None
    
    if grp_name:
        if grp_name == 'body_mid':
            grp_color = bpy.context.scene.color_set_middle
            color_collec = 'color_body.x'
        elif grp_name == 'body_left':
            grp_color = bpy.context.scene.color_set_left
            color_collec = 'color_body.l'
        elif grp_name == 'body_right':
            grp_color = bpy.context.scene.color_set_right
            color_collec = 'color_body.r'
        elif grp_name == 'yellow':
            grp_color = (1.0, 1.0, 0.0)
        elif grp_name == 'red':
            grp_color = (1.0, 0.0, 0.0)
        elif grp_name == 'kilt':
            grp_color = (0.2, 1.0, 0.3)
            
    if body_side:
        if body_side.endswith('.l'):
            grp_color = bpy.context.scene.color_set_left
            grp_name = 'body.l'
            color_collec = 'color_body.l'
        elif body_side.endswith('.r'):
            grp_color = bpy.context.scene.color_set_right
            grp_name = 'body.r'
            color_collec = 'color_body.r'
        elif body_side.endswith('.x'):
            grp_color = bpy.context.scene.color_set_middle
            grp_name = 'body.x'
            color_collec = 'color_body.x'
            
    if custom_color:
        grp_color = custom_color
        
    if custom_highlight == None:
        custom_highlight = [0.2, 0.4]
                
    if bpy.app.version >= (4,0,0):
        if color_collec:
            set_bone_layer(bone_data, color_collec, multi=True)
        
        
        if assign_only_if_empty:# do not change color group if a group is already assigned
            if bone_data.color.palette != 'DEFAULT':
                return
        
        bone_data.color.palette = 'CUSTOM' 
        
        # set normal color
        bone_data.color.custom.normal = grp_color

        # set select, active colors
        for col_idx in range(0,3):
            bone_data.color.custom.select[col_idx] = grp_color[col_idx] + custom_highlight[0]
            bone_data.color.custom.active[col_idx] = grp_color[col_idx] + custom_highlight[1]
        
    else:
        bone_pose = get_pose_bone(bone_data.name)
        if assign_only_if_empty:# do not change color group if a group is already assigned            
            if bone_pose.bone_group != None:
                return
                
        grp = obj.pose.bone_groups.get(grp_name)
        if grp == None:
            grp = obj.pose.bone_groups.new(name=grp_name)
            grp.color_set = 'CUSTOM'

            # set normal color
            grp.colors.normal = grp_color
            # set select color/active color
            for col_idx in range(0,3):
                grp.colors.select[col_idx] = grp_color[col_idx] + custom_highlight[0]
                grp.colors.active[col_idx] = grp_color[col_idx] + custom_highlight[1]

        bone_pose.bone_group = grp
    

def get_bone_colors(bone_data, list=False):
    if bone_data.color.palette == 'CUSTOM':
        if list == False:
            return bone_data.color.custom.normal, bone_data.color.custom.select, bone_data.color.custom.active
        else:
            return [i for i in bone_data.color.custom.normal], [i for i in bone_data.color.custom.select], [i for i in bone_data.color.custom.active]
    else:
        return bone_data.color.palette
    

def set_bone_color(bone_data, bcolors, assign_only_if_empty=False):
    # Blender 4 and higher only
    if assign_only_if_empty:# do not change color group if a group is already assigned
        if bone_data.color.palette != 'DEFAULT':
            return
                
    if type(bcolors) == str:# set the color palette string
        bone_data.color.palette = bcolors
    else:# set the color lists
        col_normal, col_select, col_active = bcolors
        bone_data.color.palette = 'CUSTOM'
        bone_data.color.custom.normal = col_normal
        bone_data.color.custom.select = col_select
        bone_data.color.custom.active = col_active

    
def reset_pbone_transforms(pbone):
    pbone.location = [0,0,0]
    pbone.rotation_euler = [0,0,0]
    pbone.rotation_quaternion = [1,0,0,0]
    pbone.scale = [1,1,1]     