import bpy, os, ast, random, sys, time
from bpy.types import (Operator, Menu, Panel, UIList, PropertyGroup, FloatProperty, StringProperty, BoolProperty)
from bpy.props import *
from mathutils import *
from math import *
from bpy.app.handlers import persistent
from . import auto_rig_datas as ard
from . import reset_all_controllers
from operator import itemgetter
from bpy_extras import anim_utils


# Global vars ###########################################################################################################
hands_ctrl = ["c_hand_ik", "c_hand_fk"]
sides = [".l", ".r"]
eye_aim_bones = ["c_eye_target.x", "c_eye"]
auto_eyelids_bones = ["c_eye", "c_eyelid_top", "c_eyelid_bot"]
fk_arm = ["c_arm_fk", "c_forearm_fk", "c_hand_fk", "arm_fk_pole"]
ik_arm = ["arm_ik", "forearm_ik", "c_hand_ik", "c_arms_pole", "c_arm_ik", "c_hand_ik_offset", "c_hand_ik_pivot"]
fk_leg = ["c_thigh_fk", "c_leg_fk", "c_foot_fk", "c_toes_fk", "leg_fk_pole", "c_thigh_b_fk"]
ik_leg = ["thigh_ik", "leg_ik", "c_foot_ik", "c_leg_pole", "c_toes_ik", "c_foot_01", "c_foot_roll_cursor", "foot_snap_fk", "c_thigh_ik", "c_toes_pivot", "c_foot_ik_offset", "c_thigh_b", "c_leg_ik3", "c_foot_ik_pivot"]
fingers_root = ["c_index1_base", "c_thumb1_base", "c_middle1_base", "c_ring1_base", "c_pinky1_base"]
fingers_start = ["c_thumb", "c_index", "c_middle", "c_ring", "c_pinky"]
fingers_type_list = ["thumb", "index", "middle", "ring", "pinky"]
toes_start = ["c_toes_thumb", "c_toes_index", "c_toes_middle", "c_toes_ring", "c_toes_pinky"]
spines_ctrls = ['c_spine_', 'c_root', 'c_chest']


# Utils ###########################################################################################################
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


def delete_fcurve(act, fc, slot_idx=0):
    if bpy.app.version >= (5,0,0):
        cb = anim_utils.action_ensure_channelbag_for_slot(act, act.slots[slot_idx])
        cb.fcurves.remove(fc)
    else:
        act.fcurves.remove(fc)


def create_fcurve(act, dp, slot_idx=0, fc_index=0, action_group=''):
    if bpy.app.version >= (5,0,0):
        cb = anim_utils.action_ensure_channelbag_for_slot(act, act.slots[slot_idx])
        return cb.fcurves.new(dp, index=fc_index, group_name=action_group)
    else:
        return act.fcurves.new(dp, index=fc_index, action_group=action_group)


def find_fcurve(act, dp, slot_idx=0, fc_index=0):
    if bpy.app.version >= (5,0,0):
        cb = anim_utils.action_get_channelbag_for_slot(act, act.slots[slot_idx])
        if cb == None: return None
        return cb.fcurves.find(dp, index=fc_index)
    else:
        return act.fcurves.find(data_path=dp, index=fc_index)


def is_pbone_selected(pbone):
    if bpy.app.version >= (5,0,0):
        return pbone.select
    else:
        return pbone.bone.select

        
def select_pbone(pbone, state=True):
    if bpy.app.version >= (5,0,0):
        pbone.select = state
    else:
        pbone.bone.select = state


def update_get_action_range(self, context):
    anim_d = bpy.context.active_object.animation_data
    if anim_d:
        act = anim_d.action
        if act:            
            self.frame_start = int(act.frame_range[0])
            self.frame_end = int(act.frame_range[1])


# versioning utils, update functions, must be first
def get_prefs():
    if bpy.app.version >= (4,2,0):
        pack_str = ''
        if __package__.endswith('.src'):#  rig tools files are at root
            pack_str = __package__[:-4]
        else:
            pack_str = __package__
        return bpy.context.preferences.addons[pack_str].preferences
    else:
        return bpy.context.preferences.addons[__package__.split('.')[0]].preferences


def get_armature_collections(_arm): 
    arm_data = _arm.data if 'type' in dir(_arm) else _arm
    if bpy.app.version >= (4,1,0):
        return arm_data.collections_all
    else:
        return arm_data.collections


def is_proxy(obj):
    # proxy atttribute removed in Blender 3.3
    if 'proxy' in dir(obj):
        if obj.proxy:
            return True
    return False


def get_blender_version():
    ver = bpy.app.version
    return ver[0]*100+ver[1]+ver[2]*0.01


def get_override_dict_compat():    
    if bpy.app.version >= (2,91,0):     
        return {'LIBRARY_OVERRIDABLE', 'USE_INSERTION'}
    else:      
        return {'LIBRARY_OVERRIDABLE'}


@persistent   
def rig_layers_anim_update(foo):  
    # if layers viz are animated, update on each frame
    if bpy.context.scene.arp_layers_animated:
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE':
                if 'layers_sets' in obj.keys():
                    for lay in obj.layers_sets:            
                        set_layer_vis(lay, lay.visibility_toggle)


def update_visibility_toggle(self, context):
    set_layer_vis(self, self.visibility_toggle)


def is_bone_in_layer(bone_name, layer_type):
    if bpy.app.version >= (4,0,0):
        if bpy.context.mode == 'EDIT_ARMATURE':# Armature Edit mode must be handled this way, prone to error otherwise (bone data not up to date)
            in_collection = [ebone.name for ebone in bpy.context.active_object.data.edit_bones if layer_type in ebone.collections]
            return bone_name in in_collection
        else:
            return layer_type in bpy.context.active_object.data.bones.get(bone_name).collections
    else:
        if layer_type in ard.layer_col_map_special:# layer idx special cases
            layer_idx = ard.layer_col_map_special[layer_type]
        else:# standard ARP layer-collec conversion       
            layer_idx = ard.layer_col_map[layer_type]
            
        return bpy.context.active_object.data.bones.get(bone_name).layers[layer_idx]
        
    
def update_layer_select(self, context):
    if self.update_saved_layers == False:
        return

    rig = bpy.context.active_object
    
    def select_bone(bname):
        if bpy.context.mode == 'EDIT_ARMATURE':
            b = get_edit_bone(bname)
            if b:
                b.select = True
                
        elif bpy.context.mode == 'POSE' or bpy.context.mode == 'OBJECT':
            pb = get_pose_bone(bname)
            if pb:
                select_pbone(pb)            
                
    # bones collection/layer
    if bpy.app.version >= (4,0,0):
        # get bones collections in set
        bones_collections = []
        for item in self.bonecollections_set:
            for collec in get_armature_collections(rig):
                if 'collec_id' in collec.keys():
                    if item.collec_id == collec['collec_id']:
                        bones_collections.append(collec)
                        
        # get bones in collections
        for col in bones_collections:
            for b in rig.data.bones:
                if is_bone_in_layer(b.name, col.name):
                    select_bone(b.name)
        
    else:
        for i, lay in enumerate(self.layers):
            if lay:
                for b in rig.data.bones:                
                    if b.layers[i]:
                        select_bone(b.name)     
             

    # bones list
    bones_names = ast.literal_eval(self.bones)
  
    for bname in bones_names:
        select_bone(bname)     

    
def update_layer_set_exclusive(self, context):
    if self.update_saved_layers == False:
        return
        
    rig = bpy.context.active_object
    
    # armature collections/layers
    set_layer_vis(self, True)
    
    current_layers_idx = []
    
    if bpy.app.version >= (4,0,0):
        for item in self.bonecollections_set:
            for collec in get_armature_collections(rig):
                if 'collec_id' in collec.keys():
                    if item.collec_id == collec['collec_id']:
                        if collec.is_visible:
                            current_layers_idx.append(collec.name)       
    else:
        current_layers_idx = [i for i, l in enumerate(self.layers) if l]    
    
    if self.exclusive_toggle:
        
        # save current displayed layers
        saved_layers = []
        
        if bpy.app.version >= (4,0,0):
            for collec in get_armature_collections(rig):
                if collec.is_visible:
                    saved_layers.append(collec.name)
        else:
            for i, lay in enumerate(rig.data.layers):
                if lay:
                    saved_layers.append(i)
                    
        self.exclusive_saved_layers = str(saved_layers)
        
        # hide other layers
        if len(current_layers_idx):
            if bpy.app.version >= (4,0,0):
                for col in get_armature_collections(rig):
                    if not col.name in current_layers_idx:
                        col.is_visible = False
            else:
                for i, lay in enumerate(rig.data.layers):
                    if not i in current_layers_idx:
                        rig.data.layers[i] = False
                    
    else:
        # restore saved layers  
        saved_layers = ast.literal_eval(self.exclusive_saved_layers)
        
        for i in saved_layers:
            if bpy.app.version >= (4,0,0):
                get_armature_collections(rig).get(i).is_visible = True
            else:
                rig.data.layers[i] = True
    
    # bones       
    bones_list = ast.literal_eval(self.bones)        
    
    if len(bones_list):
        if bpy.context.mode == "EDIT_ARMATURE":
            for eb in rig.data.edit_bones:
                if self.exclusive_toggle:
                    if not eb.name in bones_list:
                        eb.hide = True     
                else:
                    eb.hide = False
                    
        elif bpy.context.mode == "POSE" or bpy.context.mode == "OBJECT":
            for pb in rig.pose.bones: 
                if self.exclusive_toggle:
                    if not pb.name in bones_list:
                        if bpy.app.version >= (5,0,0):
                            pb.hide = True
                        else:
                            pb.bone.hide = True
                else:
                    if bpy.app.version >= (5,0,0):
                        pb.hide = False
                    else:
                        pb.bone.hide = False
                    
                    
    # for now, multiple exclusive layers is not possible, maybe todo later  
    # disable other exclusive toggles    
    for layerset in rig.layers_sets:           
        if layerset != self:
            layerset.update_saved_layers = False# workaround recursion depth issue
            layerset.exclusive_toggle = False
            layerset.update_saved_layers = True
            
    # objects
    # do not set objects visibility exclusively
    # how to restore hidden objects visibility that are not part of any layer?
    
    
# OPERATOR CLASSES ########################################################################################################### 
class ARP_OT_clear_root_motion(Operator):
    """Clear the character's root motion by resetting the c_traj position and rotation, while preserving the current animation and rig hierarchy"""

    bl_idname = "arp.clear_root_motion"
    bl_label = "Clear Root Motion"
    bl_options = {'UNDO'}
    
    frame_start: IntProperty(default=0)
    frame_end: IntProperty(default=10)
    get_action_range: BoolProperty(default=True, update=update_get_action_range, description='Set current action range')
    #force_full_update: BoolProperty(default=False, description='Trigger the bones data update more frequently, in order to debug incorrect results.\nLead to longer computation time, only enable if necessary')
    
    def invoke(self, context, event): 
        scn = bpy.context.scene
        rig = bpy.context.active_object
        if rig.animation_data:
            if rig.animation_data.action:
                self.frame_start = int(rig.animation_data.action.frame_range[0])
                self.frame_end = int(rig.animation_data.action.frame_range[1])
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=400)
        
    def draw(self, context):
        #layout = self.layout
        #layout.prop(self, 'force_full_update', text='Force Update')
        #layout.separator()
        draw_bake_frame_range_menu(self, draw_one_key=False)
    
    def execute(self, context):        
        _clear_root_motion(self)
        
        return {'FINISHED'}
    
        
class ARP_OT_extract_root_motion(Operator):
    """Extract the character's root motion by baking the 'c_traj' controller according to the pelvis position and rotation,\nwhile preserving the current animation and rig hierarchy"""
    bl_idname = "arp.extract_root_motion"
    bl_label = "Extract Root Motion"
    bl_options = {'UNDO'}
    
    root_type: EnumProperty(items=(
        ('ROOT_MASTER', 'c_root_master', 'Use c_root_master to extract root motion'),
        ('ROOT', 'c_root', 'Use c_root to extract root motion')
        ), description='Bone coordinates used to extract root motion')
    
    loc_x: BoolProperty(default=True, description='Use X location (World space, left/right)')
    loc_y: BoolProperty(default=True, description='Use Y location (World space, forward/backward)')
    loc_z: BoolProperty(default=False, description='Use Z location (World space, height)')
    loc_x_offset: BoolProperty(default=False, description='Keep initial offset when applying X location')
    loc_y_offset: BoolProperty(default=False, description='Keep initial offset when applying Y location')
    loc_z_offset: BoolProperty(default=True, description='Keep initial offset when applying Z location')
    rotation: BoolProperty(default=True, description='Use rotation (World space). Only the Z axis is rotated')
    forward_axis: EnumProperty(items=(
        ('X', 'X', 'X'),
        ('Y', 'Y', 'Y'),
        ('Z', 'Z', 'Z'),
        ('-X', '-X', '-X'),
        ('-Y', '-Y', '-Y'),
        ('-Z', '-Z', '-Z'),
        ), description='The c_root_master axis pointing forward, that will be used to orient the c_traj Y axis', default='Z')
    
    frame_start: IntProperty(default=0)
    frame_end: IntProperty(default=10)
    get_action_range: BoolProperty(default=True, update=update_get_action_range, description='Set current action range')
    #force_full_update: BoolProperty(default=False, description='Trigger the bones data update more frequently, in order to debug incorrect results.\nLead to longer computation time, only enable if necessary')
    
    def invoke(self, context, event): 
        scn = bpy.context.scene
        rig = bpy.context.active_object
        if rig.animation_data:
            if rig.animation_data.action:
                self.frame_start = int(rig.animation_data.action.frame_range[0])
                self.frame_end = int(rig.animation_data.action.frame_range[1])
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=400)
        
        
    def draw(self, context):
        layout = self.layout
        col = layout.column()
        row = col.row()
        row.prop(self, 'root_type', expand=True)
        row = col.row()
        row.prop(self, 'loc_x', text='Location X')
        row.prop(self, 'loc_y', text='Y')
        row.prop(self, 'loc_z', text='Z')
        col = layout.column()
        row = col.row()
        row.prop(self, 'loc_x_offset', text='Location X Offset')
        row.prop(self, 'loc_y_offset', text='Y Offset')
        row.prop(self, 'loc_z_offset', text='Z Offset')
        #col.enabled = self.loc_z
        col = layout.column()
        col.prop(self, 'rotation', text='Rotation')
        col = col.column()
        col.enabled = self.rotation
        col.label(text='Pelvis Forward Axis:')
        row = col.row(align=True)
        row.prop(self, 'forward_axis', text='Pelvis Forward Axis', expand=True)
        #col.separator()
        #col.prop(self, 'force_full_update', text='Force Update')
        col.separator()
        draw_bake_frame_range_menu(self, draw_one_key=False)
        
    def execute(self, context):        
        _extract_root_motion(self)
        
        return {'FINISHED'}
        
    
class ARP_OT_property_pin(Operator):
    """Pin the custom property to this panel (always on display even if the bone is not selected)"""
    bl_idname = "arp.property_pin"
    bl_label = "Property Pin"
    bl_options = {'UNDO'}   
    
    prop_dp_pb: StringProperty(default='')
    prop: StringProperty(default='')
    state: BoolProperty(default=True)
    
    def execute(self, context):        
        #try:
        rig = bpy.context.active_object
        pb = bpy.context.selected_pose_bones[0]
        
        if not 'arp_pinned_props' in rig.data.keys():
            create_custom_prop(node=rig.data, prop_name="arp_pinned_props", prop_val='', prop_description="Pinned custom properties")
        
        
        pinned_props_list = get_pinned_props_list(rig)
        
        def is_dp_in_list(prop_dp):
            if len(pinned_props_list):
                for prop_dp_list in pinned_props_list:                      
                    if prop_dp_list == prop_dp:                        
                        return True                 
                return False
                
            else:                
                return False
            
        
        def pin_prop(prop_dp, check=True):         
            add = False
            if check:                    
                if not is_dp_in_list(prop_dp):                  
                    add = True
            else:
                add = True
            
            if add:                  
                rig.data["arp_pinned_props"] = rig.data["arp_pinned_props"] + prop_dp + ','
                
                
        def unpin_prop(prop_dp):
            if is_dp_in_list(prop_dp):
                pinned_props_copy = [i for i in pinned_props_list]
                rig.data["arp_pinned_props"] = ''# clear   
                # copy back while skipping selected prop
                for prop_copy_dp in pinned_props_copy:
                    if prop_copy_dp == '':
                        continue
                    if prop_copy_dp != prop_dp:
                        pin_prop(prop_copy_dp, check=False)
                
                if len(rig.data["arp_pinned_props"]) == 1:
                     rig.data["arp_pinned_props"] = ''
                        
                        
        if self.state:# Pin          
            pin_prop(pb.path_from_id() + '["'+ self.prop + '"]')
        else:# Unpin       
            unpin_prop(self.prop_dp_pb + '["'+ self.prop + '"]')

            
        return {'FINISHED'}        


#   Rig Layers classes -----------------------------------------------------------
class ARP_OT_layers_add_defaults(Operator):
    """Add default Main and Secondary layer sets"""
    bl_idname = "arp.layers_add_defaults"
    bl_label = "Show All Layers Set"
    bl_options = {'UNDO'}   
  
    def execute(self, context):        
        try:           
            rig = bpy.context.active_object
    
            set1 = rig.layers_sets.add()
            set1.name = 'Main' 
            set2 = rig.layers_sets.add()
            set2.name = 'Secondary'
            
            if bpy.app.version >= (4,0,0):
                collec_main = get_armature_collections(rig).get('Main')
                if collec_main:
                    layers_set_add_collec(lay_set=set1, collec_name='Main')
                collec_secondary = get_armature_collections(rig).get('Secondary')
                if collec_secondary:
                    layers_set_add_collec(lay_set=set2, collec_name='Secondary')
            else:
                set1.layers[0] = True 
                set2.layers[1] = True
            
            rig.layers_sets_idx = len(rig.layers_sets)-1
                    
        except:
            pass
            
        return {'FINISHED'}
        
        
class ARP_OT_layers_sets_all_toggle(Operator):
    """Set all layers visibility"""
    bl_idname = "arp.layers_sets_all_toggle"
    bl_label = "Show All Layers Set"
    bl_options = {'UNDO'}   
  
    state: BoolProperty(default=True)
    
    def execute(self, context):
        rig = bpy.context.active_object           
        
        # hide all (at least the first layer must remain enabled)
        if self.state == False:
            if bpy.app.version < (4,0,0):
                rig.data.layers[0] = True
            
        for set in rig.layers_sets:
            set.visibility_toggle = self.state
            
        return {'FINISHED'}
        

class ARP_MT_layers_sets_menu(Menu):
    bl_label = "Layers Set Specials"

    def draw(self, _context):
        scn = bpy.context.scene
        layout = self.layout
        layout.operator('arp.layers_sets_edit', text="Edit Layer...")  
        layout.separator()
        layout.menu("ARP_MT_layers_sets_menu_import", text="Import", icon='IMPORT')        
        layout.menu("ARP_MT_layers_sets_menu_export", text="Export", icon='EXPORT')
        layout.separator()
        layout.operator('arp.layers_sets_all_toggle', text="Show All", icon='HIDE_OFF').state = True
        layout.operator('arp.layers_sets_all_toggle', text="Hide All", icon='HIDE_ON').state = False
        layout.separator()
        layout.prop(scn, "arp_layers_set_render", text="Set Render Visibility")
        layout.prop(scn, "arp_layers_show_exclu", text="Show Exclusive Toggle")
        layout.prop(scn, "arp_layers_show_select", text="Show Select Toggle")
        layout.prop(scn, 'arp_layers_animated', text="Animated Layers")
        

class ARP_MT_layers_sets_menu_import(Menu):
    bl_label = "Layers Set Import"
    
    custom_presets = []
    
    def draw(self, _context):
        layout = self.layout
        layout.operator("arp.layers_set_import", text="From File...")
        layout.separator()
        layout.operator("arp.layers_add_defaults", text="Add Default Layers")
        layout.separator()
        for cp in self.custom_presets:
            op = layout.operator("arp.layers_set_import_preset", text=cp.title()).preset_name = cp
        
        
class ARP_MT_layers_sets_menu_export(Menu):
    bl_label = "Layers Set Export"
    
    def draw(self, _context):
        layout = self.layout
        
        layout.operator("arp.layers_set_export", text="To File...")    
        layout.operator("arp.layers_set_export_preset", text="As New Preset...")
        
        
class ARP_OT_layers_set_import(bpy.types.Operator):
    """ Import the selected preset file"""

    bl_idname = "arp.layers_set_import"
    bl_label = "Import Preset"

    filter_glob: StringProperty(default="*.py", options={'HIDDEN'})
    filepath: StringProperty(subtype="FILE_PATH", default='py')
    
    
    def execute(self, context):
        scn = bpy.context.scene
        
        try:         
            _import_layers_sets(self)
            
        finally:
            pass
            
        return {'FINISHED'}
        

    def invoke(self, context, event):
        self.filepath = 'layers_set_preset.py'
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
        
        
class ARP_OT_layers_set_import_preset(bpy.types.Operator):
    """ Import the selected preset file"""

    bl_idname = "arp.layers_set_import_preset"
    bl_label = "Import Preset"
   
    preset_name: StringProperty(default='')
    filepath: StringProperty(subtype="FILE_PATH", default='py')
    
    
    def execute(self, context):
        scn = bpy.context.scene
        
        try:         
            # custom presets       
            custom_dir = get_prefs().rig_layers_path
            if not (custom_dir.endswith("\\") or custom_dir.endswith('/')):
                custom_dir += '/'
                
            try:
                os.listdir(custom_dir)
            except:
                self.report({'ERROR'}, 'The rig layers presets directory seems invalid: '+custom_dir+'\nCheck the path in the addon preferences')
                return
    
            self.filepath = custom_dir + self.preset_name+'.py'  
            
            _import_layers_sets(self)
            
        finally:
            pass
            
        return {'FINISHED'}

        
class ARP_OT_layers_set_export(Operator):
    """ Export the selected preset file"""

    bl_idname = "arp.layers_set_export"
    bl_label = "Export Preset"

    filter_glob: StringProperty(default="*.py", options={'HIDDEN'})
    filepath: StringProperty(subtype="FILE_PATH", default='py')
    
    
    def execute(self, context):
        scn = bpy.context.scene
        
        try:         
            _export_layers_sets(self)
            
        finally:
            pass
            
        return {'FINISHED'}
        

    def invoke(self, context, event):
        self.filepath = 'layers_set_preset.py'
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
        
        
class ARP_OT_layers_set_export_preset(Operator):
    """ Export the selected preset file"""

    bl_idname = "arp.layers_set_export_preset"
    bl_label = "Export Preset"
    
    filepath: StringProperty(subtype="FILE_PATH", default='py') 
    preset_name: StringProperty(default='CoolRigLayers')
    
    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=400)
        
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "preset_name", text="Preset Name")
        
    
    def execute(self, context):
        scn = bpy.context.scene
        
        try:        
            custom_dir = get_prefs().rig_layers_path
            if not (custom_dir.endswith("\\") or custom_dir.endswith('/')):
                custom_dir += '/'
                
            if not os.path.exists(os.path.dirname(custom_dir)):
                try:
                    os.makedirs(os.path.dirname(custom_dir))
                except:
                    pass
            """      
            try:
                os.listdir(custom_dir)
            except:
                self.report({'ERROR'}, 'The rig layers presets directory seems invalid: '+custom_dir+'\nCheck the path in the addon preferences')
                return
            """
            
            self.filepath = custom_dir + self.preset_name+'.py'  
            
            _export_layers_sets(self)
            
            update_layers_set_presets()
            
        finally:
            pass
            
        return {'FINISHED'}
        

class ARP_OT_layers_sets_remove_bones(Operator):
    """Removes all bones from the set"""
    bl_idname = "arp.layers_sets_remove_bones"
    bl_label = "Removes Bones From Set" 
  
    def execute(self, context):        
        try:   
            rig = bpy.context.active_object           
            current_set = rig.layers_sets[rig.layers_sets_idx]     
            current_set.bones = '[]'                
        except:
            pass
            
        return {'FINISHED'}
        
        
class ARP_OT_layers_sets_add_bones(Operator):
    """Add selected bones in layer set"""
    bl_idname = "arp.layers_sets_add_bones"
    bl_label = "Add Bones In Set"   
  
    def execute(self, context):        
        try:   
            rig = bpy.context.active_object           
            current_set = rig.layers_sets[rig.layers_sets_idx]
            
            # mirror must be disabled, leads to wrong selection otherwise
            mirror_state = rig.data.use_mirror_x            
            rig.data.use_mirror_x = False
            
            # get selected bones names
            sel_bones_names = []
            
            if context.mode == "POSE":
                sel_bones_names = [i.name for i in bpy.context.selected_pose_bones]
            elif context.mode == "EDIT_ARMATURE":
                sel_bones_names = [i.name for i in bpy.context.selected_editable_bones]
            
            current_list = ast.literal_eval(current_set.bones)
            add_bones_names = [i for i in sel_bones_names if not i in current_list]# check for possible doubles            
            current_set.bones = str(current_list + add_bones_names) 
            
            # restore mirror
            rig.data.use_mirror_x = mirror_state
                
        except:
            pass
            
        return {'FINISHED'}
        
        
class ARP_OT_layers_sets_clear_objects(Operator):
    """Clear all objects in set"""
    bl_idname = "arp.layers_sets_clear_objects"
    bl_label = "Clear Objects In Set"   
  
    def execute(self, context):        
        try:   
            rig = bpy.context.active_object           
            current_set = rig.layers_sets[rig.layers_sets_idx]
            
            while len(current_set.objects_set):
                current_set.objects_set.remove(0)
                
        except:
            pass
            
        return {'FINISHED'}        
        
        
class ARP_OT_layers_sets_add_object(Operator):
    """Add object in layer set"""
    bl_idname = "arp.layers_sets_add_object"
    bl_label = "Add Object In Set"   
  
    def execute(self, context):        
        try:   
            rig = bpy.context.active_object           
            current_set = rig.layers_sets[rig.layers_sets_idx]
           
            # check if it's not already in the set
            found = False
            for item in current_set.objects_set:
                if item.object_item == current_set.object_to_add:
                    found = True             
                    break                
        
            # add object entry
            if not found:
                if current_set.object_to_add != None:
                    obj_set = current_set.objects_set.add()
                    obj_set.object_item = current_set.object_to_add
                
        except:
            pass
            
        return {'FINISHED'}   


class ARP_OT_layers_sets_remove_collection(Operator):
    """Delete the selected bone collection from the layer set"""

    bl_idname = "arp.delete_bone_collec"
    bl_label = ""
    bl_options = {'UNDO'}

    collec_id : StringProperty(default='')
   
    def execute(self, context):
        rig = bpy.context.active_object
        current_set = rig.layers_sets[rig.layers_sets_idx]
      
        if self.collec_id != '':           
            for idx, item in enumerate(current_set.bonecollections_set):              
                if item.collec_id == self.collec_id:
                    current_set.bonecollections_set.remove(idx)
                
        return {'FINISHED'}        

 
def generate_collec_id(collec_name):
    # generate 10 random indexes as unique identifier
    rand_indexes = ''
    for i in range(0,10):
        rand_indexes += str(random.randint(1, 10))
    return collec_name + rand_indexes
    
 
def layers_set_add_collec(lay_set=None, collec_name=None):
    # if lay_set is None, use active layer set in the list
    # if collec_name is None, use collec name set in the Layer Edit dialog
    
    rig = bpy.context.active_object  

    if lay_set == None:
        current_set = rig.layers_sets[rig.layers_sets_idx]
    else:
        current_set = lay_set
    
    if collec_name == None:
        collec_name = current_set.collection_to_add
    
    # get the collection id
    collec_to_add_id = None
    collec_to_add = get_armature_collections(rig).get(collec_name)
    if collec_to_add == None:
        return
        
    if 'collec_id' in collec_to_add.keys():
        collec_to_add_id = collec_to_add['collec_id']
    
    # check if it's not already in the set
    found = False
    if collec_to_add_id != None:# if no ID yet, hasn't been added
        for item in current_set.bonecollections_set:
            if item.collec_id == collec_to_add_id:
                found = True
                break                

    # add collection ID
    if not found:            
        if collec_name != None:
            new_collec_set = current_set.bonecollections_set.add()
            new_collec_id = generate_collec_id(collec_name)
            new_collec_set.collec_id = new_collec_id    
            collec_to_add['collec_id'] = new_collec_id
            

class ARP_OT_layers_sets_add_collection(Operator):
    """Add bone collection in layer set"""
    bl_idname = "arp.layers_sets_add_collection"
    bl_label = "Add Collection In Set"   
  
    def execute(self, context):        
        layers_set_add_collec()
        
        return {'FINISHED'}
        

class ObjectSet(PropertyGroup):
    object_item : PointerProperty(type=bpy.types.Object)
    
    
class BoneCollectionSet(PropertyGroup):
    collec_id : StringProperty(default='')#PointerProperty(type=bpy.types.BoneCollection) does not work, sigh... tag collection with a string identifier instead

 
class LayerSet(PropertyGroup):  
    exclusive_toggle_desc = 'Only show this layer'
    select_toggle_desc = 'Select bones in this layer'
    objects_set_desc = 'Collection of objects in this set'
    visibility_toggle_desc = 'Show or hide this layer'
    
    if bpy.app.version >= (2,90,0):
        name : StringProperty(default='', description='Limb Name', override={'LIBRARY_OVERRIDABLE'})        
        layers: BoolVectorProperty(size=32, default=(False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False), subtype='LAYER', override={'LIBRARY_OVERRIDABLE'})      
        objects_set : CollectionProperty(type=ObjectSet, description=objects_set_desc, override=get_override_dict_compat())
        bonecollections_set: CollectionProperty(type=BoneCollectionSet, description='Collection of bones in this set', override=get_override_dict_compat())
        collection : PointerProperty(type=bpy.types.Collection, override={'LIBRARY_OVERRIDABLE'}) 
        collection_to_add: StringProperty(default='', override={'LIBRARY_OVERRIDABLE'})
        object_to_add: PointerProperty(type=bpy.types.Object, override={'LIBRARY_OVERRIDABLE'})        
        visibility_toggle: BoolProperty(default=True, update=update_visibility_toggle, override={'LIBRARY_OVERRIDABLE'}, description=visibility_toggle_desc, options={'ANIMATABLE'})       
        exclusive_toggle: BoolProperty(default=False, update=update_layer_set_exclusive, override={'LIBRARY_OVERRIDABLE'}, description=exclusive_toggle_desc)
        select_toggle: BoolProperty(default=True, update=update_layer_select, override={'LIBRARY_OVERRIDABLE'}, description=select_toggle_desc)
        show_objects: BoolProperty(default=True, override={'LIBRARY_OVERRIDABLE'})
        show_bones: BoolProperty(default=False, override={'LIBRARY_OVERRIDABLE'})
        bones: StringProperty(default="[]", override={'LIBRARY_OVERRIDABLE'})
        exclusive_saved_layers: StringProperty(default='[]', override={'LIBRARY_OVERRIDABLE'})
        update_saved_layers: BoolProperty(default=True, override={'LIBRARY_OVERRIDABLE'})
    else:# no overrides before 290
        name : StringProperty(default="", description="Limb Name")       
        layers: BoolVectorProperty(size=32, default=(False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False), subtype='LAYER')      
        objects_set : CollectionProperty(type=ObjectSet, description=objects_set_desc)
        collection : PointerProperty(type=bpy.types.Collection)   
        object_to_add: PointerProperty(type=bpy.types.Object)  
        visibility_toggle: BoolProperty(default=True, update=update_visibility_toggle, description=visibility_toggle_desc, options={'ANIMATABLE'})       
        exclusive_toggle: BoolProperty(default=False, update=update_layer_set_exclusive, description=exclusive_toggle_desc)    
        select_toggle: BoolProperty(default=True, update=update_layer_select, description=select_toggle_desc)        
        show_objects: BoolProperty(default=True)
        show_bones: BoolProperty(default=False)
        bones: StringProperty(default="[]")
        exclusive_saved_layers: StringProperty(default='[]')    
        update_saved_layers: BoolProperty(default=True)    


class ARP_UL_layers_sets_list(UIList):  
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        scn = bpy.context.scene
        row = layout.row(align=True)
        row.prop(item, "name", text="", emboss=False, translate=False)# icon='BONE_DATA')
        if scn.arp_layers_show_select:
            row.prop(item, "select_toggle", text="", icon='RESTRICT_SELECT_OFF', emboss=False)
        row.prop(item, 'visibility_toggle', text='', icon='HIDE_OFF' if item.visibility_toggle else 'HIDE_ON', emboss=False)      
        #row.prop(item, "show_toggle", text="", icon='HIDE_OFF', emboss=False)
        #row.prop(item, "hide_toggle", text="", icon='HIDE_ON', emboss=False)   
        if scn.arp_layers_show_exclu:
            icon_name = 'SOLO_ON' if item.exclusive_toggle else 'SOLO_OFF'            
            row.prop(item, "exclusive_toggle", text="", icon=icon_name, emboss=False)#icon='LAYER_ACTIVE'
        
        
    def invoke(self, context, event):
        pass
        
        
class ARP_OT_layers_sets_move(Operator):
    """Move entry"""
    bl_idname = "arp.layers_sets_move"
    bl_label = "Move Layer Set"
    bl_options = {'UNDO'}   
  
    direction: StringProperty(default="UP")
    
    def execute(self, context):        
        try:   
            rig = bpy.context.active_object
            fac = -1
            if self.direction == 'DOWN':
                fac = 1
                
            target_idx = rig.layers_sets_idx + fac
            if target_idx < 0:
                target_idx = len(rig.layers_sets)-1
            if target_idx > len(rig.layers_sets)-1:
                target_idx = 0

            rig.layers_sets.move(rig.layers_sets_idx, target_idx)
            rig.layers_sets_idx = target_idx
            
        except:
            pass
        return {'FINISHED'}
  

class ARP_PT_layers_sets_edit(Operator):
    """Edit a layer set"""
    bl_idname = "arp.layers_sets_edit"
    bl_label = "Edit Layer Set"
    bl_options = {'UNDO'}
    
    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)
   
    def draw(self, context):
        draw_layer_set_edit(self, context)        
    
    def execute(self, context):    
        return {'FINISHED'}    
  
  
class ARP_OT_layers_sets_add(Operator):
    """Add a layer set"""
    bl_idname = "arp.layers_sets_add"
    bl_label = "Add Layer"
    bl_options = {'UNDO'}
    
    def invoke(self, context, event):
        # add new layer set with default settings
        _add_layer_set(self)
        
        # open dialog
        wm = context.window_manager
        return wm.invoke_props_dialog(self)
   
    def draw(self, context):
        draw_layer_set_edit(self, context)        
    
    def execute(self, context):    
        return {'FINISHED'}    
        
        
class ARP_OT_layers_sets_remove(Operator):
    """Remove a layer set"""
    bl_idname = "arp.layers_sets_remove"
    bl_label = "Remove Layer"
    bl_options = {'UNDO'}

    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False

        try:       
            _remove_layer_set(self)
        finally:
            context.preferences.edit.use_global_undo = use_global_undo
        return {'FINISHED'} 
        
   
#   End Rig Layers classes --------------------------------------------------------------------   

class ARP_OT_childof_keyer(Operator):
    """Keyframe the influence of all Child Of constraints of this bone"""
    
    bl_idname = "arp.childof_keyer"
    bl_label = "Child Of Keyframer"
    bl_options = {'UNDO'}    
  
    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.mode == 'POSE')
 

    def execute(self, context):
        
        if len(bpy.context.selected_pose_bones) == 0:
            self.report({'ERROR'}, "A bone must be selected")
            return {'FINISHED'}
        
        for pb in bpy.context.selected_pose_bones:
            try:            
                _childof_keyer(pb)
            finally:
                pass
            
        return {'FINISHED'}


class ARP_OT_childof_switcher(Operator):
    """Switch and snap to the selected Child Of constraint (parent space)"""
    
    bl_idname = "arp.childof_switcher"
    bl_label = "Switch and snap Child Of constraints"
    bl_options = {'UNDO'}
    
    cns_items = []     
    
    def get_cns_items(self, context):
        return ARP_OT_childof_switcher.cns_items        

    child_of_cns: EnumProperty(items=get_cns_items, default=None)
    curr_child_of_cns: StringProperty(default='')
    bake_type: EnumProperty(items=(('STATIC', 'Static', 'Switch and snap only for the current frame'), ('ANIM', 'Anim', 'Switch and snap over a specified frame range')), default='STATIC')
    frame_start: IntProperty(default=0)
    frame_end: IntProperty(default=10)
    one_key_per_frame: BoolProperty(default=True, description="Insert one keyframe per frame if enabled, otherwise only existing keyframes within the given frame range will be keyframed (less accurate)", name="Key All Frames")
    get_action_range: BoolProperty(default=True, update=update_get_action_range, description='Set current action range')
    
    
    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.mode == 'POSE')        
       

    def invoke(self, context, event):   
        ARP_OT_childof_switcher.cns_items = []       
        active_bone = None
        self.curr_child_of_cns = ''
        try:
            active_bone = bpy.context.selected_pose_bones[0]
        except:
            pass
            
        if active_bone == None:
            self.report({'ERROR'}, "A bone must be selected")
            return {'FINISHED'}            
        
        active_cns = None
        last_cns = None
        
        # collect current ChildOf constraints
        if len(active_bone.constraints):
            # get active one first, but do not add it to the parent list
            for cns in active_bone.constraints:  
                if not cns.enabled:# filter out muted constraints
                    continue
                if cns.type == 'CHILD_OF':                    
                    if cns.influence > 0:
                        active_cns = cns
                        separator = ''
                        if cns.subtarget != '':
                            separator = ': '
                        self.curr_child_of_cns = cns.name+'|'+cns.target.name+separator+cns.subtarget
                        break                        
        
            # others. Add them to the parents list
            for cns in active_bone.constraints: 
                if not cns.enabled:
                    continue
                if cns.type == 'CHILD_OF':                    
                    if cns != active_cns or active_cns == None:     
                        separator = ''
                        if cns.subtarget != '':
                            separator = ': '
                        last_cns = cns.name
                        ARP_OT_childof_switcher.cns_items.append((cns.name, cns.target.name + separator + cns.subtarget, ''))

        # Add None parent in option, only if the current parent is not already None
        if active_cns != None:
            ARP_OT_childof_switcher.cns_items.append(('NONE', 'None', 'None'))        
        
        # Set the last inactive constraint as default
        if last_cns != None:
            self.child_of_cns = last_cns
        
        # no valid constraints found, exit
        if len(ARP_OT_childof_switcher.cns_items) == 0:
            self.report({'ERROR'}, 'No ChildOf constraint found on this bone')
            return {'FINISHED'}
            
        # set frame start and endswith
        if context.active_object.animation_data and context.active_object.animation_data.action:
            act = context.active_object.animation_data.action
            self.frame_start, self.frame_end = int(act.frame_range[0]), int(act.frame_range[1])            
            
            
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=400)
        
        
    def draw(self, context):
        layout = self.layout
        if self.curr_child_of_cns != '':
            layout.label(text='Active Parent:           '+self.curr_child_of_cns.split('|')[1])#self.cns_items[0][1])
        else:
            layout.label(text='Active Parent:           '+'None')#self.cns_items[0][1])
        layout.prop(self, 'child_of_cns', text='Snap To')
        
        layout.prop(self, 'bake_type', expand=True)
        
        if self.bake_type == 'ANIM':
            draw_bake_frame_range_menu(self)
        
        layout.separator()
        

    def execute(self, context):
    
        try:      
            if self.bake_type == 'STATIC':
                _childof_switcher(self)
                
            elif self.bake_type == 'ANIM':
                # set autokey on
                autokey_state = context.scene.tool_settings.use_keyframe_insert_auto
                context.scene.tool_settings.use_keyframe_insert_auto = True
                
                context.scene.frame_set(self.frame_start)
                
                pb = context.selected_pose_bones[0]     
                armature = bpy.context.active_object
                
                # store current transforms
                saved_transforms = {}
                for i in range(self.frame_start, self.frame_end+1):
                    context.scene.frame_set(i)
                    saved_transforms[i] = pb.location.copy(), pb.rotation_euler.copy(), pb.rotation_quaternion.copy(), pb.scale.copy()                    
                                
                # store current constraint influences
                cns_dict = {}
                
                for cns in pb.constraints:
                    if not cns.enabled:
                        continue
                    if cns.type == 'CHILD_OF':
                        cns_dict[cns.name] = cns.influence
                
                
                frames_idx = []
                if not self.one_key_per_frame:
                    bname = pb.name
                    
                    for fc in get_action_fcurves(armature.animation_data.action):
                        if fc.data_path.startswith('pose.bones["'+bname+'"].'):
                            for keyf in fc.keyframe_points:
                                if keyf.co[0] >= self.frame_start and keyf.co[0] <= self.frame_end:
                                    if not keyf.co[0] in frames_idx:
                                        frames_idx.append(keyf.co[0])
                                
                
                # snap
                for i in range(self.frame_start, self.frame_end+1):
                
                    if not self.one_key_per_frame:# only existing keyframes?
                        if not i in frames_idx:
                            continue
                          
                    context.scene.frame_set(i)
                    
                    # and constraints
                    for cns_name in cns_dict:
                        pb.constraints.get(cns_name).influence = cns_dict[cns_name]
                    
                    # reset the initial transforms          
                    pb.location, pb.rotation_euler, pb.rotation_quaternion, pb.scale = saved_transforms[i]
                    
                    update_transform()# need update hack
                    
                    _childof_switcher(self)
                   
                # restore autokey state
                context.scene.tool_settings.use_keyframe_insert_auto = autokey_state
                    
        finally:
            pass
            
        return {'FINISHED'}
        
        
class ARP_OT_rotation_mode_convert(Operator):
    """Convert bones to euler or quaternion rotation"""
    
    bl_idname = "arp.convert_rot_mode"
    bl_label = "Convert Rotation Mode"
    bl_options = {'UNDO'}        
   
    mode: StringProperty(default="rotation_quaternion")
    frame_start: IntProperty(default=0, description="Start frame")
    frame_end: IntProperty(default=10, description="End frame")
    one_key_per_frame: BoolProperty(default=False, description="Insert one keyframe per frame if enabled, otherwise only existing keyframes within the given frame range will be keyframed", name="Key All Frames")
    #key_rot_mode: BoolProperty(default=False, description="Keyframe the rotation mode if enabled. Useful when mixing multiple rotation modes in the same action", name="Key Rotation Mode")   
    selected_only: BoolProperty(default=True, description="Only convert selected bones rotation if enabled, otherwise all animated bones", name='Selected Bones Only')
    euler_order: EnumProperty(items=(('XYZ', 'XYZ', 'XYZ'), ('XZY', 'XZY', 'XZY'), ('YXZ', 'YXZ', 'YXZ'), ('YZX', 'YZX', 'YZX'), ('ZXY', 'ZXY', 'ZXY'), ('ZYX', 'ZYX', 'ZYX')), description='Euler order', name='Euler Order')
    text_title = ''
    get_action_range: BoolProperty(default=True, update=update_get_action_range, description='Set current action range')
    
    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.mode == 'POSE')        
        

    def invoke(self, context, event):        
        action = context.active_object.animation_data.action
        if action == None:
            self.report({'ERROR'}, "This only works for animated bones")
            return {'FINISHED'}
            
        self.frame_start, self.frame_end = int(action.frame_range[0]), int(action.frame_range[1])
        
        self.text_title = 'Quaternions' if self.mode == 'rotation_quaternion' else 'Euler'
    
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=400)
        
        
    def draw(self, context):
        layout = self.layout
        layout.label(text='To '+self.text_title)
        layout.prop(self, 'selected_only')        
        if self.mode == 'rotation_euler':
            layout.prop(self, 'euler_order')

        draw_bake_frame_range_menu(self)
        

    def execute(self, context):
    
        try:
            convert_rot_mode(self)

        finally:
            pass
            
        return {'FINISHED'}

     
class ARP_OT_switch_snap_root_tip_all(Operator):
    """Switch and snap all fingers IK Root-Tip"""

    bl_idname = 'arp.switch_snap_root_tip_all'
    bl_label = 'switch_snap_root_tip_all'
    bl_options = {'UNDO'}

    side : StringProperty(name='bone side')
    finger_root_name: StringProperty(name='', default='')
    state: StringProperty(default='')

    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.mode == 'POSE')

    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False

        try:            
            for fing_type in fingers_start:
                finger_root_name = fing_type+'1_base'+self.side
                finger_root = get_pose_bone(finger_root_name)
                
                # missing finger
                if finger_root == None: continue
                
                # backward-compatibility, check if the tip target is there
                ik_target_tip_name = fing_type+'_ik'+self.side
                if get_pose_bone(ik_target_tip_name) == None:
                    print(ik_target_tip_name, 'was not found')
                    self.report({'ERROR'}, 'Missing feature (old rig). Update fingers IK by clicking Limb Options > OK')
                    context.preferences.edit.use_global_undo = use_global_undo
                    return {'FINISHED'}
                    
                # switch and snap
                if self.state == 'ROOT':
                    root_to_tip_finger(finger_root, self.side)
                elif self.state == 'TIP':
                    tip_to_root_finger(finger_root, self.side)

        finally:
            context.preferences.edit.use_global_undo = use_global_undo

        return {'FINISHED'}


class ARP_OT_switch_all_fingers(Operator):
    """Set all fingers to IK or FK"""

    bl_idname = "arp.switch_all_fingers"
    bl_label = "switch_all_fingers"
    bl_options = {'UNDO'}

    state: StringProperty(default='')
    side: StringProperty(default='')

    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.mode == 'POSE')

    def execute(self, context):
    
        # disable mirror
        mirr_state = context.active_object.pose.use_mirror_x
        context.active_object.pose.use_mirror_x = False
    
        try:
            for fing_type in fingers_start:
                finger_root_name = fing_type+'1_base'+self.side
                finger_root = get_pose_bone(finger_root_name)

                if finger_root:
                    if 'ik_fk_switch' in finger_root.keys():
                        if self.state == 'IK':
                            ik_to_fk_finger(finger_root, self.side)

                        elif self.state == 'FK':
                            fk_to_ik_finger(finger_root, self.side)
        
        finally:
            # restore mirror
            context.active_object.pose.use_mirror_x = mirr_state

        return {'FINISHED'}


class ARP_OT_free_parent_ik_fingers(Operator):
    """Enable or disable the Child Of constraints of all fingers IK target"""

    bl_idname = "arp.free_lock_ik_fingers"
    bl_label = "free_lock_ik_fingers"
    bl_options = {'UNDO'}

    side: StringProperty(default="")

    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.mode == 'POSE')

    def execute(self, context):
        try:
            for fing_type in fingers_start:
                ik_target_name = fing_type+"_ik"+self.side
                ik_target2_name = fing_type+"_ik2"+self.side
                ik_target_pb = get_pose_bone(ik_target_name)
                ik_target2_pb = get_pose_bone(ik_target2_name)

                for b in [ik_target_pb, ik_target2_pb]:
                    if b == None:
                        continue
                    if len(b.constraints) == 0:
                        continue

                    hand_cns = b.constraints.get("Child Of_hand")
                    if hand_cns:
                        if hand_cns.influence > 0.5:# set free
                            mat = b.matrix.copy()
                            hand_cns.influence = 0.0
                            b.matrix = mat

                        else:# parent
                            mat = b.matrix.copy()
                            bone_parent = get_pose_bone(hand_cns.subtarget)
                            hand_cns.influence = 1.0
                            b.matrix = bone_parent.matrix_channel.inverted() @ mat


        finally:
            pass

        return {'FINISHED'}


class ARP_OT_snap_head(Operator):
    """Switch the Head Lock and snap the head rotation"""

    bl_idname = "arp.snap_head"
    bl_label = "snap_head"
    bl_options = {'UNDO'}

    side : StringProperty(name="Side", default="")

    @classmethod
    def poll(cls, context):
        if context.object != None:
            if is_object_arp(context.object):
                return True

    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False
        try:
            bname = get_selected_pbone_name()
            self.side = get_bone_side(bname)
            _snap_head(self.side)

        finally:
            context.preferences.edit.use_global_undo = use_global_undo
        return {'FINISHED'}
        
        
class ARP_OT_snap_head_bake(Operator):
    """Snaps and bake Head Lock over a specified frame range"""
    
    bl_idname = "pose.arp_bake_head_lock"
    bl_label = "Snaps and bake Head Lock over a specified frame range"
    bl_options = {'UNDO'}
    
    side : StringProperty(name="bone side")
    frame_start : IntProperty(name="Frame start", default=0)# defined in invoke()
    frame_end : IntProperty(name="Frame end", default=10)# defined in invoke()
    get_sel_side: BoolProperty(default=True)
    one_key_per_frame: BoolProperty(default=True, description="Insert one keyframe per frame if enabled, otherwise only existing keyframes within the given frame range will be keyframed (less accurate)", name="Key All Frames")
    get_action_range: BoolProperty(default=True, update=update_get_action_range, description='Set current action range')
    
    
    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.mode == 'POSE')
    
    
    def draw(self, context):
        layout = self.layout
        draw_bake_frame_range_menu(self)


    def invoke(self, context, event):
        self.get_sel_side = True
        scn = bpy.context.scene
        self.frame_start = scn.frame_start if scn.use_preview_range == False else scn.frame_preview_start
        self.frame_end = scn.frame_end if scn.use_preview_range == False else scn.frame_preview_end
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=400)


    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False
        scn = context.scene
        
        # save current autokey state
        auto_key_state = bpy.context.scene.tool_settings.use_keyframe_insert_auto
        # set auto key to False for faster updates
        bpy.context.scene.tool_settings.use_keyframe_insert_auto = False
        # save current frame
        cur_frame = scn.frame_current

        try:
            if self.get_sel_side:
                bname = get_selected_pbone_name()
                self.side = get_bone_side(bname)

            _bake_snap_head(self)
         
        finally:
            context.preferences.edit.use_global_undo = use_global_undo
            # restore autokey state
            scn.tool_settings.use_keyframe_insert_auto = auto_key_state
            # restore frame
            scn.frame_set(cur_frame)
        
        return {'FINISHED'}


class ARP_OT_reset_script(Operator):
    """Reset character controllers to rest position"""

    bl_idname = "arp.reset_pose"
    bl_label = "reset_pose"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.object != None:
            if is_object_arp(context.object):
                return True

    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False

        try:
            reset_all_controllers.reset_all_controllers()

        finally:
            context.preferences.edit.use_global_undo = use_global_undo

        return {'FINISHED'}


class ARP_OT_set_picker_camera_func(Operator):
    """Display the bone picker of the selected character in this active view"""

    bl_idname = "id.set_picker_camera_func"
    bl_label = "set_picker_camera_func"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.object != None:
            if is_object_arp(context.object):
                return True

    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False

        try:
            _set_picker_camera(self)

        finally:
            context.preferences.edit.use_global_undo = use_global_undo
        return {'FINISHED'}


class ARP_OT_toggle_multi(Operator):
    """Toggle multi-limb visibility"""

    bl_idname = "id.toggle_multi"
    bl_label = "toggle_multi"
    bl_options = {'UNDO'}

    limb : StringProperty(name="Limb")
    id : StringProperty(name="Id")
    key : StringProperty(name="key")
    """
    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.mode == 'POSE')
    """

    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False

        try:
            _toggle_multi(self.limb, self.id, self.key)
        finally:
            context.preferences.edit.use_global_undo = use_global_undo
        return {'FINISHED'}


class ARP_OT_snap_pin(Operator):
    """Switch and snap the pinning bone"""

    bl_idname = "pose.arp_snap_pin"
    bl_label = "Arp Switch and Snap Pin"
    bl_options = {'UNDO'}

    side : StringProperty(name="bone side")
    type : StringProperty(name="bone side")

    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.mode == 'POSE')

    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False
        try:
            bname = get_selected_pbone_name()
            self.side = get_bone_side(bname)

            if is_selected(fk_arm, bname) or is_selected(ik_arm, bname):
                self.type = "arm"
            elif is_selected(fk_leg, bname) or is_selected(ik_leg, bname):
                self.type = "leg"

            _switch_snap_pin(self.side, self.type)

        finally:
            context.preferences.edit.use_global_undo = use_global_undo

        return {'FINISHED'}
        
        
class ARP_OT_bake_limb_lock(Operator):
    """Snaps and bake Arm Lock over a specified frame range"""
    
    bl_idname = "pose.arp_bake_limb_lock"
    bl_label = "Snaps and bake Arm Lock over a specified frame range"
    bl_options = {'UNDO'}
    
    side : StringProperty(name="bone side")
    bone_type : StringProperty(name="arm or leg")
    frame_start : IntProperty(name="Frame start", default=0)# defined in invoke()
    frame_end : IntProperty(name="Frame end", default=10)# defined in invoke()
    get_sel_side: BoolProperty(default=True)
    one_key_per_frame: BoolProperty(default=True, description="Insert one keyframe per frame if enabled, otherwise only existing keyframes within the given frame range will be keyframed (less accurate)", name="Key All Frames")
    get_action_range: BoolProperty(default=True, update=update_get_action_range, description='Set current action range')
    
    
    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.mode == 'POSE')
    
    
    def draw(self, context):
        layout = self.layout
        draw_bake_frame_range_menu(self)


    def invoke(self, context, event):
        self.get_sel_side = True
        scn = bpy.context.scene
        self.frame_start = scn.frame_start if scn.use_preview_range == False else scn.frame_preview_start
        self.frame_end = scn.frame_end if scn.use_preview_range == False else scn.frame_preview_end
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=400)


    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False
        scn = context.scene
        
        # save current autokey state
        auto_key_state = bpy.context.scene.tool_settings.use_keyframe_insert_auto
        # set auto key to False for faster update
        bpy.context.scene.tool_settings.use_keyframe_insert_auto = False
        # save current frame
        cur_frame = scn.frame_current

        try:
            if self.get_sel_side:
                bname = get_selected_pbone_name()
                self.side = get_bone_side(bname)
                
            if is_selected(fk_arm, bname):
                self.bone_type = "arm"
            elif is_selected(fk_leg, bname):
                self.bone_type = "leg"

            _bake_limb_lock(self)
            
        finally:
            context.preferences.edit.use_global_undo = use_global_undo
            # restore autokey state
            scn.tool_settings.use_keyframe_insert_auto = auto_key_state
            # restore frame
            scn.frame_set(cur_frame)
        
        return {'FINISHED'}


class ARP_OT_snap_limb_lock(Operator):
    """Switch and snap the arm/leg lock value"""

    bl_idname = "pose.arp_snap_limb_lock"
    bl_label = "Arp Switch and Snap Arm/Leg Lock"
    bl_options = {'UNDO'}

    side : StringProperty(name="bone side")
    bone_type : StringProperty(name="arm or leg")

    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.mode == 'POSE')

    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False
        try:
            bname = get_selected_pbone_name()
            self.side = get_bone_side(bname)
            
            if is_selected(fk_arm, bname):
                self.bone_type = "arm"
            elif is_selected(fk_leg, bname):
                self.bone_type = "leg"
                
            _snap_limb_lock(self)

        finally:
            context.preferences.edit.use_global_undo = use_global_undo

        return {'FINISHED'}

        
def draw_bake_frame_range_menu(self, draw_one_key=True):
    layout = self.layout
   
    if 'multi_select' in self.__annotations__:
        if len(self.selected_sides ) > 1:
            layout.prop(self, 'multi_select', text='All Selected Limbs ('+str(len(self.selected_sides))+')')
    
    if draw_one_key:
        col = layout.column(align=True)
        col.prop(self, 'one_key_per_frame')
        col.separator()
    
    row = layout.column().row(align=True)
    row.prop(self, 'frame_start', text='Frame Start')
    row.prop(self, 'frame_end', text='Frame End')
   
    row.prop(self, 'get_action_range', text='', icon='TIME', emboss=False)
    layout.separator()


class ARP_OT_bake_pole(Operator):
    """Snaps and bake IK Pole Parent over a specified frame range"""
    
    bl_idname = "pose.arp_bake_pole"
    bl_label = "Snaps and bake IK Pole Parent"
    bl_options = {'UNDO'}
    
    side : StringProperty(name="bone side")
    bone_type : StringProperty(name="arm or leg")
    frame_start : IntProperty(name="Frame start", default=0)
    frame_end : IntProperty(name="Frame end", default=10)
    get_sel_side: BoolProperty(default=True)
    one_key_per_frame: BoolProperty(default=True, description="Insert one keyframe per frame if enabled, otherwise only existing keyframes within the given frame range will be keyframed (less accurate)", name="Key All Frames")
    get_action_range: BoolProperty(default=True, update=update_get_action_range, description='Set current action range')
    space_target : EnumProperty(items=(('GLOBAL', 'Global', 'Global space'),
                                   ('LOCAL', 'Local', 'Local space'),
                                   ('SMART', 'Smart', 'Smart space')),
                                   description='Select the space to snap to', default='SMART')
    multi_cns: BoolProperty(default=False)
    current_space = StringProperty(default='')
    
    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.mode == 'POSE')
    
    def invoke(self, context, event):
        self.multi_cns = False
        self.get_sel_side = True
        bname = get_selected_pbone_name()
        self.side = get_bone_side(bname)
        
        if is_selected(fk_arm, bname) or is_selected(ik_arm, bname):
            self.bone_type = 'arms'
        elif is_selected(fk_leg, bname) or is_selected(ik_leg, bname):
            self.bone_type = 'leg'         
        
        if self.bone_type == 'leg':
            pole = get_pose_bone('c_leg_pole'+self.side)
            if len(pole.constraints) > 2:
                self.multi_cns = True
                
                # pre-select the other space
                if pole['pole_parent'] == 0:# global
                    self.current_space = 'GLOBAL'
                    self.space_target = 'SMART'
                elif pole['pole_parent'] == 1:# foot
                    self.current_space = 'LOCAL'
                    self.space_target = 'SMART'
                elif pole['pole_parent'] == 2:# smart
                    self.current_space = 'SMART'
                    self.space_target = 'GLOBAL'
        
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=400)
        
    
    def draw(self, context):
        if self.multi_cns:
            layout = self.layout
            layout.label(text='Active Pole Space: '+self.current_space.title())
            layout.prop(self, 'space_target', text='Snap To')
            
        draw_bake_frame_range_menu(self)


    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False
        scn = context.scene
        
        # save current autokey state
        auto_key_state = bpy.context.scene.tool_settings.use_keyframe_insert_auto
        # set auto key to True
        bpy.context.scene.tool_settings.use_keyframe_insert_auto = True
        # save current frame
        cur_frame = scn.frame_current

        try:
            _bake_pole_parent(self, space_target=self.space_target if self.multi_cns else None)
            
        finally:
            context.preferences.edit.use_global_undo = use_global_undo
            # restore autokey state
            scn.tool_settings.use_keyframe_insert_auto = auto_key_state
            # restore frame
            scn.frame_set(cur_frame)
        
        return {'FINISHED'}
        
        
class ARP_OT_snap_pole(Operator):
    """Switch and snap the IK pole parent"""

    bl_idname = "pose.arp_snap_pole"
    bl_label = "Snap IK Pole Parent"
    bl_options = {'UNDO'}

    side : StringProperty(name='bone side')
    bone_type : StringProperty(name='arm or leg')
    multi_cns: BoolProperty(default=False)
    space_target : EnumProperty(items=(('GLOBAL', 'Global', 'Global space'),
                                   ('LOCAL', 'Local', 'Local space'),
                                   ('SMART', 'Smart', 'Smart space')),
                                   description='Select the space to snap to', default='SMART')
                                   
    current_space = StringProperty(default='')  
    
    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.mode == 'POSE')
        
        
    def invoke(self, context, event):
        self.multi_cns = False
        bname = get_selected_pbone_name()
        self.side = get_bone_side(bname)

        if is_selected(fk_arm, bname) or is_selected(ik_arm, bname):
            self.bone_type = 'arms'
        elif is_selected(fk_leg, bname) or is_selected(ik_leg, bname):
            self.bone_type = 'leg'
                
        if self.bone_type == 'leg':
            pole = get_pose_bone('c_leg_pole'+self.side)
            if len(pole.constraints) > 2:
                self.multi_cns = True
                # pre-select the other space
                if pole['pole_parent'] == 0:# global
                    self.current_space = 'GLOBAL'
                    self.space_target = 'SMART'
                elif pole['pole_parent'] == 1:# foot
                    self.current_space = 'LOCAL'
                    self.space_target = 'SMART'
                elif pole['pole_parent'] == 2:# smart
                    self.current_space = 'SMART'
                    self.space_target = 'GLOBAL'
                    
                wm = context.window_manager
                return wm.invoke_props_dialog(self, width=400)

        self.execute(context)
        return {'PASS_THROUGH'}
        

    def draw(self, context):
        layout = self.layout
        layout.label(text='Active Pole Space: '+self.current_space.title())
        layout.prop(self, 'space_target', text='Snap To')
        

    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False

        try:
            _snap_pole(context.active_object, self.side, self.bone_type, space_target=self.space_target if self.multi_cns else None)

        finally:
            context.preferences.edit.use_global_undo = use_global_undo

        return {'FINISHED'}


class ARP_OT_arm_bake_fk_to_ik(Operator):
    """Snaps and bake an FK to an IK arm over a specified frame range"""
    
    bl_idname = "pose.arp_bake_arm_fk_to_ik"
    bl_label = "Snap an FK to IK arm over a specified frame range"
    bl_options = {'UNDO'}
    
    side : StringProperty(name="bone side")
    frame_start : IntProperty(name="Frame start", default=0)# defined in invoke()
    frame_end : IntProperty(name="Frame end", default=10)# defined in invoke()
    get_sel_side: BoolProperty(default=True)
    one_key_per_frame: BoolProperty(default=True, description="Insert one keyframe per frame if enabled, otherwise only existing keyframes within the given frame range will be keyframed (less accurate)", name="Key All Frames")
    get_action_range: BoolProperty(default=True, update=update_get_action_range, description='Set current action range')    
    multi_select: BoolProperty(default=True, description='Bake all selected arms or only active one')
    selected_sides = []
    
    
    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.mode == 'POSE')
    
    
    def invoke(self, context, event):
        self.get_sel_side = True
        scn = bpy.context.scene
        self.frame_start = scn.frame_start if scn.use_preview_range == False else scn.frame_preview_start
        self.frame_end = scn.frame_end if scn.use_preview_range == False else scn.frame_preview_end
        self.selected_sides = []
        
        # multi selection support
        for b in bpy.context.selected_pose_bones:
            if is_selected(fk_arm, b.name) or is_selected(ik_arm, b.name):  
                _s = get_bone_side(b.name)
                if not _s in self.selected_sides:
                    self.selected_sides.append(_s)
        
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=400)
    
    
    def draw(self, context):
        layout = self.layout
        draw_bake_frame_range_menu(self)
    
    
    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False
        scn = context.scene
        
        # save current autokey state
        auto_key_state = bpy.context.scene.tool_settings.use_keyframe_insert_auto
        # set auto key to False for faster update
        bpy.context.scene.tool_settings.use_keyframe_insert_auto = False
        # save current frame
        cur_frame = scn.frame_current

        try:
            if self.get_sel_side:
                bname = get_selected_pbone_name()
                self.side = get_bone_side(bname)
            
            if not self.multi_select:
                self.selected_sides = [self.side]
            
            bake_fk_to_ik_arm(self)
            
        finally:
            context.preferences.edit.use_global_undo = use_global_undo
            # restore autokey state
            scn.tool_settings.use_keyframe_insert_auto = auto_key_state
            # restore frame
            scn.frame_set(cur_frame)

        return {'FINISHED'}


class ARP_OT_arm_fk_to_ik(Operator):
    """Snaps an FK arm to an IK arm"""

    bl_idname = "pose.arp_arm_fk_to_ik_"
    bl_label = "Arp Snap FK arm to IK"
    bl_options = {'UNDO'}

    side : StringProperty(name="bone side")

    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.mode == 'POSE')

    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False

        try:
            bname = get_selected_pbone_name()
            self.side = get_bone_side(bname)

            fk_to_ik_arm(context.active_object, self.side)

        finally:
            context.preferences.edit.use_global_undo = use_global_undo

        return {'FINISHED'}


class ARP_OT_arm_bake_ik_to_fk(Operator):
    """Snaps and bake an IK to an FK arm over a specified frame range"""

    bl_idname = "pose.arp_bake_arm_ik_to_fk"
    bl_label = "Snap an IK to FK arm over a specified frame range"
    bl_options = {'UNDO'}

    side : StringProperty(name="bone side", default='')
    frame_start : IntProperty(name="Frame start", default=0)# default defined in invoke()
    frame_end : IntProperty(name="Frame end", default=10)# default defined in invoke()
    get_sel_side: BoolProperty(default=True)
    one_key_per_frame: BoolProperty(default=True, description="Insert one keyframe per frame if enabled, otherwise only existing keyframes within the given frame range will be keyframed (less accurate)", name="Key All Frames")
    get_action_range: BoolProperty(default=True, update=update_get_action_range, description='Set current action range')
    multi_select: BoolProperty(default=True, description='Bake all selected arms or only active one')
    selected_sides = []
    
    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.mode == 'POSE')
        
    
    def invoke(self, context, event):        
        self.get_sel_side = True
        scn = bpy.context.scene
        self.frame_start = scn.frame_start if scn.use_preview_range == False else scn.frame_preview_start
        self.frame_end = scn.frame_end if scn.use_preview_range == False else scn.frame_preview_end
        self.selected_sides = []
        
        # multi selection support
        for b in bpy.context.selected_pose_bones:
            if is_selected(fk_arm, b.name) or is_selected(ik_arm, b.name):  
                _s = get_bone_side(b.name)
                if not _s in self.selected_sides:
                    self.selected_sides.append(_s)
                    
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=400)
        
    
    def draw(self, context):
        draw_bake_frame_range_menu(self)
    
    
    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False
        scn = context.scene
        
        # save current autokey state
        auto_key_state = scn.tool_settings.use_keyframe_insert_auto
        # set auto key to False for faster updates
        scn.tool_settings.use_keyframe_insert_auto = False
        # save current frame
        cur_frame = scn.frame_current

        try:
            if self.get_sel_side:
                bname = get_selected_pbone_name()
                self.side = get_bone_side(bname)
            
            if not self.multi_select:
                self.selected_sides = [self.side]
                
            bake_ik_to_fk_arm(self)
            
        finally:
            context.preferences.edit.use_global_undo = use_global_undo
            # restore autokey state
            scn.tool_settings.use_keyframe_insert_auto = auto_key_state
            # restore frame
            scn.frame_set(cur_frame)

        return {'FINISHED'}


class ARP_OT_arm_ik_to_fk(Operator):
    """Snaps an IK arm to an FK arm"""

    bl_idname = "pose.arp_arm_ik_to_fk_"
    bl_label = "Arp Snap IK arm to FK"
    bl_options = {'UNDO'}

    side : StringProperty(name="bone side")

    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.mode == 'POSE')

    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False

        try:
            bname = get_selected_pbone_name()
            self.side = get_bone_side(bname)

            ik_to_fk_arm(context.active_object, self.side)

        finally:
            context.preferences.edit.use_global_undo = use_global_undo
        return {'FINISHED'}
        

class ARP_OT_switch_snap_root_tip(Operator):
    """Switch and snap fingers IK Root-Tip"""

    bl_idname = "arp.switch_snap_root_tip"
    bl_label = "switch_snap_root_tip"
    bl_options = {'UNDO'}

    side : StringProperty(name="bone side")
    finger_root_name: StringProperty(name='', default='')

    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.mode == 'POSE')

    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False
        
        # disable mirror
        mirr_state = context.active_object.pose.use_mirror_x
        context.active_object.pose.use_mirror_x = False
        
        try:
            bname = get_selected_pbone_name()
            self.side = get_bone_side(bname)

            finger_type = ''
            for type in fingers_type_list:
                if type in bname:
                    finger_type = type
                    break

            self.finger_root_name = 'c_'+finger_type+'1_base'+self.side
            root_finger = get_pose_bone(self.finger_root_name)
            
            # backward-compatibility, check if the tip target is there
            ik_target_tip_name = 'c_'+finger_type+'_ik'+self.side
            if get_pose_bone(ik_target_tip_name) == None:
                self.report({'ERROR'}, 'Missing feature (old rig). Update fingers IK by clicking Limb Options > OK')
                context.preferences.edit.use_global_undo = use_global_undo
                return {'FINISHED'}
                

            if root_finger['ik_tip'] < 0.5:
                tip_to_root_finger(root_finger, self.side)
            else:
                root_to_tip_finger(root_finger, self.side)

        finally:
            # restore mirror
            context.active_object.pose.use_mirror_x = mirr_state
            
            context.preferences.edit.use_global_undo = use_global_undo

        return {'FINISHED'}
        

class ARP_OT_snap_reversed_spine(Operator):
    """Switch and snap the forward-reversed spine"""

    bl_idname = 'pose.arp_snap_reversed_spine'
    bl_label = 'Arp Switch and Snap Reversed Spine'
    bl_options = {'UNDO'}

    side : StringProperty(name='bone side')   

    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.mode == 'POSE')

    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False

        try:
            bname = get_selected_pbone_name()
            self.side = get_bone_side(bname)
            c_root_master_pb = get_pose_bone('c_root_master'+self.side)
          
            if c_root_master_pb['reverse_spine'] < 0.5:
                snap_spine_rev_to_fwd(self.side)
            else:
                snap_spine_fwd_to_rev(self.side)
            
        finally:
            context.preferences.edit.use_global_undo = use_global_undo

        return {'FINISHED'}


class ARP_OT_switch_snap(Operator):
    """Switch and snap the IK-FK"""

    bl_idname = 'pose.arp_switch_snap'
    bl_label = 'Arp Switch and Snap IK FK'
    bl_options = {'UNDO'}

    side : StringProperty(name='bone side')
    type : StringProperty(name='type', default='')
    finger_root_name: StringProperty(name='', default='')
    spline_name: StringProperty(name='', default='')
    all: BoolProperty(default=False)
    toe_type: StringProperty(default='')

    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.mode == 'POSE')

    def execute(self, context):
        # disable undo
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False        
        
        # disable mirror
        mirr_state = context.active_object.pose.use_mirror_x
        context.active_object.pose.use_mirror_x = False
        
        used_sides = []
        
        try:
            for b in bpy.context.selected_pose_bones:
                bname = b.name                 
                #bname = get_selected_pbone_name()
                self.side = get_bone_side(bname)
                
                # make sure to only switch the same side once, in case multiple bones are selected from the same side
                if self.side in used_sides:
                    continue
                    
                used_sides.append(self.side)
                
                #   get type
                if is_selected(fk_leg, bname) or is_selected(ik_leg, bname):
                    self.type = 'LEG'
                elif is_selected(toes_start, bname, startswith=True):
                    self.type = 'TOE'
                elif is_selected(fk_arm, bname) or is_selected(ik_arm, bname):
                    self.type = 'ARM'
                elif is_selected(fingers_start, bname, startswith=True):
                    self.type = 'FINGER'

                    finger_type = None
                    for type in fingers_type_list:
                        if type in bname:
                            finger_type = type
                            break

                    self.finger_root_name = 'c_'+finger_type+'1_base'+self.side 
                    
                elif is_selected('c_spline_', bname, startswith=True) or is_selected_prop(context.active_pose_bone, 'arp_spline'):
                    self.type = 'SPLINE_IK'
                   
                #   snap
                if self.type == 'ARM':
                    hand_ik = get_pose_bone(ik_arm[2] + self.side)
                    if hand_ik['ik_fk_switch'] < 0.5:
                        fk_to_ik_arm(context.active_object, self.side)
                    else:
                        ik_to_fk_arm(context.active_object, self.side)

                elif self.type == 'LEG':
                    foot_ik = get_pose_bone(ik_leg[2] + self.side)
                    if foot_ik['ik_fk_switch'] < 0.5:
                        fk_to_ik_leg(context.active_object, self.side)
                    else:
                        ik_to_fk_leg(context.active_object, self.side)

                elif self.type == 'TOE':
                    toes_list = [self.toe_type]
                    if self.all:
                        for i in ['thumb','index','middle','ring','pinky']:
                            if i != self.toe_type:
                                toes_list.append(i)
                    
                    for fing_type in toes_list:
                        other_root_name = self.finger_root_name.replace(self.toe_type, fing_type)
                        root_toe = get_pose_bone(other_root_name)
                        if root_toe:# toe may be disabled
                            if root_toe['ik_fk_switch'] < 0.5:
                                fk_to_ik_toe(root_toe, self.side)
                            else:
                                ik_to_fk_toe(root_toe, self.side)
                        
                elif self.type == 'FINGER':
                    root_finger = get_pose_bone(self.finger_root_name)
                    if root_finger['ik_fk_switch'] < 0.5:
                        fk_to_ik_finger(root_finger, self.side)
                    else:
                        ik_to_fk_finger(root_finger, self.side)

                elif self.type == 'SPLINE_IK':
                    c_spline_root = get_pose_bone('c_'+self.spline_name+'_root'+self.side)
                    if 'ik_fk_switch' in c_spline_root.keys():
                        if c_spline_root['ik_fk_switch'] < 0.5:
                            fk_to_ik_spline(context.active_object, self.spline_name, self.side)
                        else:
                            ik_to_fk_spline(context.active_object, self.spline_name, self.side)
            
        finally:
            # restore mirror
            context.active_object.pose.use_mirror_x = mirr_state
            # restore undo
            context.preferences.edit.use_global_undo = use_global_undo

        return {'FINISHED'}


class ARP_OT_leg_bake_fk_to_ik(Operator):
    """Snaps and bake an FK leg to an IK leg over a specified frame range"""

    bl_idname = "pose.arp_bake_leg_fk_to_ik"
    bl_label = "Snap an FK to IK leg over a specified frame range"
    bl_options = {'UNDO'}

    side : StringProperty(name="bone side")
    get_sel_side: BoolProperty(default=True)
    frame_start : IntProperty(name="Frame start", default=0)# defined in invoke()
    frame_end : IntProperty(name="Frame end", default=10)# defined in invoke()
    temp_frame_start = 0
    temp_frame_end = 1
    one_key_per_frame: BoolProperty(default=True, description="Insert one keyframe per frame if enabled, otherwise only existing keyframes within the given frame range will be keyframed (less accurate)", name="Key All Frames")
    get_action_range: BoolProperty(default=True, update=update_get_action_range, description='Set current action range')
    multi_select: BoolProperty(default=True, description='Bake all selected legs or only active one')
    selected_sides = []
    
    
    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.mode == 'POSE')

        
    def invoke(self, context, event):
        self.get_sel_side = True
        scn = bpy.context.scene
        self.frame_start = scn.frame_start if scn.use_preview_range == False else scn.frame_preview_start
        self.frame_end = scn.frame_end if scn.use_preview_range == False else scn.frame_preview_end
        self.selected_sides = []
        
        # multi selection support
        for b in bpy.context.selected_pose_bones:
            if is_selected(fk_leg, b.name) or is_selected(ik_leg, b.name):  
                _s = get_bone_side(b.name)
                if not _s in self.selected_sides:
                    self.selected_sides.append(_s)
                    
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=400)
        
        
    def draw(self, context):
        draw_bake_frame_range_menu(self)
        

    def set_range():
        ARP_OT_leg_bake_fk_to_ik.frame_start = ARP_OT_leg_bake_fk_to_ik.temp_frame_start
        ARP_OT_leg_bake_fk_to_ik.frame_end = ARP_OT_leg_bake_fk_to_ik.temp_frame_end


    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False
        scn = context.scene
        
        # save current autokey state
        auto_key_state = scn.tool_settings.use_keyframe_insert_auto
        # set auto key to False for faster update
        scn.tool_settings.use_keyframe_insert_auto = False
        # save current frame
        cur_frame = scn.frame_current
        
        try:
            if self.get_sel_side:
                bname = get_selected_pbone_name()
                self.side = get_bone_side(bname)
                
            if not self.multi_select:
                self.selected_sides = [self.side]
                
            bake_fk_to_ik_leg(self)
            
        finally:
            context.preferences.edit.use_global_undo = use_global_undo
            # restore autokey state
            scn.tool_settings.use_keyframe_insert_auto = auto_key_state
            # restore frame
            scn.frame_set(cur_frame)
            
        return {'FINISHED'}


class ARP_OT_leg_fk_to_ik(Operator):
    """Snaps an FK leg to an IK leg"""

    bl_idname = "pose.arp_leg_fk_to_ik_"
    bl_label = "Arp Snap FK leg to IK"
    bl_options = {'UNDO'}

    side : StringProperty(name="bone side")
    

    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.mode == 'POSE')

    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False

        try:
            bname = get_selected_pbone_name()
            self.side = get_bone_side(bname)

            fk_to_ik_leg(context.active_object, self.side)

        finally:
            context.preferences.edit.use_global_undo = use_global_undo
        return {'FINISHED'}


class ARP_OT_leg_bake_ik_to_fk(Operator):
    """Snaps and bake an IK leg to an FK leg over a specified frame range"""

    bl_idname = "pose.arp_bake_leg_ik_to_fk"
    bl_label = "Snap an IK to FK leg over a specified frame range"
    bl_options = {'UNDO'}

    side : StringProperty(name="bone side")
    get_sel_side: BoolProperty(default=True)
    frame_start : IntProperty(name="Frame start", default=0)# defined in invoke()
    frame_end : IntProperty(name="Frame end", default=10)# defined in invoke()
    one_key_per_frame: BoolProperty(default=True, description="Insert one keyframe per frame if enabled, otherwise only existing keyframes within the given frame range will be keyframed (less accurate)", name="Key All Frames")
    get_action_range: BoolProperty(default=True, update=update_get_action_range, description='Set current action range')
    multi_select: BoolProperty(default=True, description='Bake all selected legs or only active one')
    selected_sides = []
    
    
    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.mode == 'POSE')
        

    def draw(self, context):
        layout = self.layout
        draw_bake_frame_range_menu(self)
        

    def invoke(self, context, event):
        self.get_sel_side = True
        scn = bpy.context.scene
        self.frame_start = scn.frame_start if scn.use_preview_range == False else scn.frame_preview_start
        self.frame_end = scn.frame_end if scn.use_preview_range == False else scn.frame_preview_end
        self.selected_sides = []
        
        # multi selection support
        for b in bpy.context.selected_pose_bones:
            if is_selected(fk_leg, b.name) or is_selected(ik_leg, b.name):  
                _s = get_bone_side(b.name)
                if not _s in self.selected_sides:
                    self.selected_sides.append(_s)
                    
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=400)

    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False
        scn = context.scene
        
        # save current autokey state
        auto_key_state = bpy.context.scene.tool_settings.use_keyframe_insert_auto
        # set auto key to False for faster update
        bpy.context.scene.tool_settings.use_keyframe_insert_auto = False
        # save current frame
        cur_frame = scn.frame_current

        try:
            if self.get_sel_side:
                bname = get_selected_pbone_name()
                self.side = get_bone_side(bname)
                
            if not self.multi_select:
                self.selected_sides = [self.side]
                
            bake_ik_to_fk_leg(self)
            
        finally:
            context.preferences.edit.use_global_undo = use_global_undo
            # restore autokey state
            scn.tool_settings.use_keyframe_insert_auto = auto_key_state
            # restore frame
            scn.frame_set(cur_frame)

        return {'FINISHED'}


class ARP_OT_leg_ik_to_fk(Operator):
    """Snaps an IK leg to an FK leg"""

    bl_idname = "pose.arp_leg_ik_to_fk_"
    bl_label = "Arp Snap IK leg to FK"
    bl_options = {'UNDO'}

    side : StringProperty(name="bone side")

    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.mode == 'POSE')

    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False
        try:
            bname = get_selected_pbone_name()
            self.side = get_bone_side(bname)

            ik_to_fk_leg(context.active_object, self.side)
        finally:
            context.preferences.edit.use_global_undo = use_global_undo

        return {'FINISHED'}

        
class ARP_OT_toes_set_all(Operator):
    """Apply to all toes"""

    bl_idname = "pose.arp_toes_set_all"
    bl_label = "Arp Toes Set All"
    bl_options = {'UNDO'}

    prop_name : StringProperty(default='')
    root_name: StringProperty(default='')
    toe_type: StringProperty(default='')
    
    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.mode == 'POSE')

    def execute(self, context):
    
        sel_root_pb = get_pose_bone(self.root_name)
        current_prop_val = sel_root_pb[self.prop_name]
        
        for fing_type in ['thumb','index','middle','ring','pinky']:
            other_root_name = self.root_name.replace(self.toe_type, fing_type)
            root_pb = get_pose_bone(other_root_name)
            if root_pb:# toe may be disabled
                root_pb[self.prop_name] = current_prop_val
        
        update_transform()# need update hack

        return {'FINISHED'}

  
class ARP_OT_spline_bake_fk_to_ik(Operator):
    """Snaps and bake an FK to an IK spline chain over a specified frame range"""
    
    bl_idname = "pose.arp_bake_spline_fk_to_ik"
    bl_label = "Snap an FK to IK spline over a specified frame range"
    bl_options = {'UNDO'}
    
    side: StringProperty(name="bone side")
    spline_name: StringProperty(name='')
    frame_start: IntProperty(name="Frame start", default=0)# defined in invoke()
    frame_end: IntProperty(name="Frame end", default=10)# defined in invoke()
    get_sel_side: BoolProperty(default=True)
    one_key_per_frame: BoolProperty(default=True, description="Insert one keyframe per frame if enabled, otherwise only existing keyframes within the given frame range will be keyframed (less accurate)", name="Key All Frames")
    get_action_range: BoolProperty(default=True, update=update_get_action_range, description='Set current action range')
    
    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.mode == 'POSE')
    
    
    def invoke(self, context, event):
        self.get_sel_side = True
        scn = bpy.context.scene
        self.frame_start = scn.frame_start if scn.use_preview_range == False else scn.frame_preview_start
        self.frame_end = scn.frame_end if scn.use_preview_range == False else scn.frame_preview_end
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=400)
    
    
    def draw(self, context):
        draw_bake_frame_range_menu(self)
        
    
    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False
        scn = context.scene
        
        auto_key_state = bpy.context.scene.tool_settings.use_keyframe_insert_auto
        bpy.context.scene.tool_settings.use_keyframe_insert_auto = False
        cur_frame = scn.frame_current

        try:
            if self.get_sel_side:
                bname = get_selected_pbone_name()
                self.side = get_bone_side(bname)

            bake_fk_to_ik_spline(self)
            
        finally:
            context.preferences.edit.use_global_undo = use_global_undo
            scn.tool_settings.use_keyframe_insert_auto = auto_key_state
            scn.frame_set(cur_frame)

        return {'FINISHED'}
        
        
class ARP_OT_spline_bake_ik_to_fk(Operator):
    """Snaps and bake an IK to an FK spline chain over a specified frame range"""
    
    bl_idname = "pose.arp_bake_spline_ik_to_fk"
    bl_label = "Snap an IK to FK spline over a specified frame range"
    bl_options = {'UNDO'}
    
    side: StringProperty(name="bone side")
    spline_name: StringProperty(name='')
    frame_start: IntProperty(name="Frame start", default=0)# defined in invoke()
    frame_end: IntProperty(name="Frame end", default=10)# defined in invoke()
    get_sel_side: BoolProperty(default=True)
    one_key_per_frame: BoolProperty(default=True, description="Insert one keyframe per frame if enabled, otherwise only existing keyframes within the given frame range will be keyframed (less accurate)", name="Key All Frames")
    get_action_range: BoolProperty(default=True, update=update_get_action_range, description='Set current action range')
    
    
    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.mode == 'POSE')
    

    def invoke(self, context, event):
        self.get_sel_side = True
        scn = bpy.context.scene
        self.frame_start = scn.frame_start if scn.use_preview_range == False else scn.frame_preview_start
        self.frame_end = scn.frame_end if scn.use_preview_range == False else scn.frame_preview_end
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=400)
        
        
    def draw(self, context):
        draw_bake_frame_range_menu(self)


    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False
        scn = context.scene
        
        auto_key_state = bpy.context.scene.tool_settings.use_keyframe_insert_auto
        bpy.context.scene.tool_settings.use_keyframe_insert_auto = False
        cur_frame = scn.frame_current        
        
        try:
            if self.get_sel_side:
                bname = get_selected_pbone_name()
                self.side = get_bone_side(bname)

            bake_ik_to_fk_spline(self)
            
        finally:
            context.preferences.edit.use_global_undo = use_global_undo
            scn.tool_settings.use_keyframe_insert_auto = auto_key_state
            scn.frame_set(cur_frame)

        return {'FINISHED'}
        
        
# UTILS --------------------------------------------------------------

#   Utils Misc
def update_transform():   
    # hack to trigger the update with a blank rotation operator
    bpy.ops.transform.rotate(value=0, orient_axis='Z', orient_type='VIEW', orient_matrix=((0.0, 0.0, 0), (0, 0.0, 0.0), (0.0, 0.0, 0.0)), orient_matrix_type='VIEW', mirror=False)
    
    
#   Utils Bones

def is_selected(names, selected_bone_name, startswith=False):
    bone_side = get_bone_side(selected_bone_name)
    if startswith == False:
        if type(names) == list:
            for name in names:
                if not '.' in name[-2:]:
                    if name + bone_side == selected_bone_name:
                        return True
                else:
                    if name[-2:] == '.x':
                        if name[:-2] + bone_side == selected_bone_name:
                            return True
        elif names == selected_bone_name:
            return True
    else:# startswith
        if type(names) == list:
            for name in names:
                if selected_bone_name.startswith(name):
                    return True
        else:
            return selected_bone_name.startswith(names)
    return False


def is_selected_prop(pbone, prop_name):
    if pbone.bone.keys():
        if prop_name in pbone.bone.keys():
            return True
            

def get_data_bone(name):
    return bpy.context.active_object.data.bones.get(name)
    

def get_pose_bone(name):
    return bpy.context.active_object.pose.bones.get(name)
    
    
def get_edit_bone(name):
    return bpy.context.active_object.data.edit_bones.get(name)


def get_selected_pbone_name():
    try:
        return bpy.context.selected_pose_bones[0].name#bpy.context.active_pose_bone.name
    except:
        return
        

def get_bone_side(bone_name):
    side = ""
    if not "_dupli_" in bone_name:
        side = bone_name[-2:]
    else:
        side = bone_name[-12:]
    return side
    
    
def set_pose_rotation(pose_bone, mat):
    q = mat.to_quaternion()

    if pose_bone.rotation_mode == 'QUATERNION':
        pose_bone.rotation_quaternion = q
    elif pose_bone.rotation_mode == 'AXIS_ANGLE':
        pose_bone.rotation_axis_angle[0] = q.angle
        pose_bone.rotation_axis_angle[1] = q.axis[0]
        pose_bone.rotation_axis_angle[2] = q.axis[1]
        pose_bone.rotation_axis_angle[3] = q.axis[2]
    else:
        pose_bone.rotation_euler = q.to_euler(pose_bone.rotation_mode)
        
     
def snap_bone_matrix(pose_bone, tar_mat, updt=True):
    # Snap a bone to a defined transform matrix
    # Supports child of constraints and parent

    if pose_bone.parent:       
        pose_bone.matrix = tar_mat.copy()
        if updt:
            update_transform()
    else:
        # ChildOf constraint support
        child_of_cns = None
        for cns in pose_bone.constraints:
            if cns.type == 'CHILD_OF' and cns.influence > 0 and cns.enabled and cns.target:
                if cns.subtarget != '' and get_pose_bone(cns.subtarget):
                    child_of_cns = cns
                    break
       
        if child_of_cns:
            pose_bone.matrix = get_pose_bone(child_of_cns.subtarget).matrix_channel.inverted_safe() @ tar_mat
        else:
            pose_bone.matrix = tar_mat.copy()
        
        if updt:
            update_transform()
            

def snap_rot(pose_bone, target_bone):
    mat = get_pose_matrix_in_other_space(target_bone.matrix, pose_bone)
    set_pose_rotation(pose_bone, mat)
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.mode_set(mode='POSE')
    

def zero_out_pb(pbone):
    pbone.location = [0,0,0]
    pbone.rotation_euler = [0,0,0]
    pbone.rotation_quaternion = [1,0,0,0]
    pbone.scale = [1,1,1]     
    
    
def set_bone_matrix_cns_simple(bone_src, mat_tar):
    # set a bone matrix with constraint compensation
    # simple method that evaluates the constraint transformation matrix as a translation
    # only works with constraints like ChildOf, influence = 1
    
    # disable inters constraints
    cns_states = []
    for cns in bone_src.constraints:
        cns_states.append(cns.enabled)
        cns.enabled = False
        
    update_transform()
    
    # apply target matrix
    bone_src.matrix = mat_tar.copy()
    update_transform()
    mat_no_cns = bone_src.matrix.copy()
    
    # enable constraints
    for ci, cns in enumerate(bone_src.constraints):
        cns.enabled = cns_states[ci]
    
    update_transform()
    
    # compensate constraints offset
    mat_cns = bone_src.matrix.copy()
    mat_diff = mat_cns.inverted() @ mat_no_cns
    bone_src.matrix = mat_no_cns @ mat_diff
    
    # stretch/scale not supported, zero out
    bone_src.scale = [1,1,1]
    update_transform()
    
    
def set_bone_matrix_cns_iter(bone_src, mat_tar, iter_max=10):
    # set a bone matrix with constraint compensation
    # use iterative approach to determine the constraint transformation
    # works with any constraint, any influence value
    
    def mute_constraints(pb):
        cns_states = []
        for cns in pb.constraints:
            cns_states.append(cns.enabled)
            cns.enabled = False
        return cns_states
    
    def unmute_constraints(pb, cns_states):
        for ci, cns in enumerate(pb.constraints):
            cns.enabled = cns_states[ci]
    
    prev_mat = None
    prec = bpy.context.scene.arp_spline_snap_precision
    
    for i in range(0, iter_max):
        # get the matrix without constraints applied
        cns_states = mute_constraints(bone_src)
        update_transform()        
        mat_no_cns = bone_src.matrix.copy()

        # compute matrix diff with constraints applied
        unmute_constraints(bone_src, cns_states)
        update_transform()
        mat_diff = mat_tar.inverted() @ bone_src.matrix
        
        # snap
        mat_def = mat_no_cns @ mat_diff.inverted()
        bone_src.matrix = mat_def
        
        # evaluate precision
        if prev_mat:
            compare = compare_mat(bone_src.matrix, prev_mat, prec)
            if compare:
                #print('Matched with', i, 'iterations, prec =', prec)                
                break
            
        prev_mat = bone_src.matrix.copy()
        
    
# Utils Anim
def store_keyframe(bone_name, prop_type, fc_array_index, frame, value, keyframes_dict):
    fc_data_path = 'pose.bones["' + bone_name + '"].'+prop_type
    fc_key = (fc_data_path, fc_array_index)
    
    if not bone_name in keyframes_dict:
        keyframes_dict[bone_name] = {fc_key: []}        
    dico = keyframes_dict[bone_name]
    if not fc_key in dico:
        dico[fc_key] = []
    dico[fc_key].extend((frame, value))        
    keyframes_dict[bone_name] = dico


def store_loc_key(pbone, f, keyframes):
    for arr_idx, value in enumerate(pbone.location):
        store_keyframe(pbone.name, "location", arr_idx, f, value, keyframes)


def store_rot_key(pbone, f, euler_prevs, quat_prevs, keyframes):
    rotation_mode = pbone.rotation_mode
    
    if rotation_mode == 'QUATERNION':
        quat_prev = None
        if not pbone.name in quat_prevs:
            quat_prevs[pbone.name] = {f: None}
        if f-1 in quat_prevs[pbone.name]:
            quat_prev = quat_prevs[pbone.name][f-1]
        
        if quat_prev is not None:
            quat = pbone.rotation_quaternion.copy()
            if bpy.app.version >= (2,82,0):# previous versions don't know this function
                quat.make_compatible(quat_prev)
            pbone.rotation_quaternion = quat
            quat_prevs[pbone.name][f] = quat
            del quat
        else:
            quat_prevs[pbone.name][f] = pbone.rotation_quaternion.copy()
        for arr_idx, value in enumerate(pbone.rotation_quaternion):
            store_keyframe(pbone.name, "rotation_quaternion", arr_idx, f, value, keyframes)

    elif rotation_mode == 'AXIS_ANGLE':
        for arr_idx, value in enumerate(pbone.rotation_axis_angle):
            store_keyframe(pbone.name, "rotation_axis_angle", arr_idx, f, value, keyframes)

    else:# euler, XYZ, ZXY etc        
        euler_prev = None
        if not pbone.name in euler_prevs:
            euler_prevs[pbone.name] = {f: None}   
        if f-1 in euler_prevs[pbone.name]:
            euler_prev = euler_prevs[pbone.name][f-1]
        
        if euler_prev != None:
            euler = pbone.matrix_basis.to_euler(pbone.rotation_mode, euler_prev)
            pbone.rotation_euler = euler                      
            del euler

        euler_prevs[pbone.name][f] = pbone.rotation_euler.copy()
        
        for arr_idx, value in enumerate(pbone.rotation_euler):
            store_keyframe(pbone.name, "rotation_euler", arr_idx, f, value, keyframes)
    
    
def get_keyf_data(key):
    return [key.co[0], key.co[1], key.handle_left[0], key.handle_left[1], key.handle_right[0], key.handle_right[1],
                key.handle_left_type, key.handle_right_type, key.easing, key.interpolation]
                
                
def set_keyf_data(key, data):
    key.co[0] = data[0]
    key.co[1] = data[1]
    key.handle_left[0] = data[2]
    key.handle_left[1] = data[3]
    key.handle_right[0] = data[4]
    key.handle_right[1] = data[5]
    key.handle_left_type = data[6]
    key.handle_right_type = data[7]
    key.easing = data[8]    
    key.interpolation = data[9]
    
    
def keyframe_pb_transforms(pb, loc=True, rot=True, scale=True, keyf_locked=False, fcurve_insert=False, action=None):    
    if loc:
        if fcurve_insert and action:
            dp = 'pose.bones["'+pb.name+'"].location'
            
            for i in range(0,3):
                fcurve = find_fcurve(action, dp, fc_index=i)
                if fcurve == None:
                    fcurve = create_fcurve(action, dp, fc_index=i, action_group=pb.name)
                fcurve.keyframe_points.insert(bpy.context.scene.frame_current, pb.location[i])
            
        else:
            for i, j in enumerate(pb.lock_location):
                if not j or keyf_locked:
                    pb.keyframe_insert(data_path='location', index=i)  
    if rot:
        if fcurve_insert and action:
            dp = 'pose.bones["'+pb.name+'"].rotation_euler'
            
            for i in range(0,3):
                fcurve = find_fcurve(action, dp, fc_index=i)
                if fcurve == None:
                    fcurve = create_fcurve(action, dp, fc_index=i, action_group=pb.name)
                fcurve.keyframe_points.insert(bpy.context.scene.frame_current, pb.rotation_euler[i])
        
        else:    
            rot_dp = 'rotation_quaternion' if pb.rotation_mode == 'QUATERNION' else 'rotation_euler' 
            rot_locks = [i for i in pb.lock_rotation]
            if rot_dp == 'rotation_quaternion':
                rot_locks.insert(0, pb.lock_rotation_w)
            for i, j in enumerate(rot_locks):
                if not j or keyf_locked:
                    pb.keyframe_insert(data_path=rot_dp, index=i)
        
    if scale:
        for i, j in enumerate(pb.lock_scale):
            if not j or keyf_locked:
                pb.keyframe_insert(data_path='scale', index=i)


def insert_keyframes(action, keyframes, start=0, end=10):
    for bone_name in keyframes:
        dico = keyframes[bone_name]
        for fc_key, key_values in dico.items():
            data_path, _index = fc_key            
            fcurve = find_fcurve(action, data_path, fc_index=_index)
            curr_fc_keyf_data = []
            if fcurve:
                curr_fc_keyf_data = [get_keyf_data(key) for key in fcurve.keyframe_points]
                delete_fcurve(action, fcurve)

            fcurve = create_fcurve(action, data_path, fc_index=_index, action_group=bone_name)

            # set keyframes points
            num_keys = len(key_values) // 2
            fcurve.keyframe_points.add(num_keys)
            fcurve.keyframe_points.foreach_set('co', key_values)
            
            # set interpolation type
            key_interp = 'LINEAR'
        
            if bpy.app.version >= (2,90,0):# internal error when doing so with Blender 2.83, only for Blender 2.90 and higher
                interp_value = bpy.types.Keyframe.bl_rna.properties['interpolation'].enum_items[key_interp].value                    
                fcurve.keyframe_points.foreach_set('interpolation', (interp_value,) * num_keys)
             
            else:
                for kf in fcurve.keyframe_points:
                    # set interpolation type (pre Blender 2.90 versions)
                    kf.interpolation = key_interp
                    
            fcurve.update()
            
            # restore initial keyframes, out of the frame range only
            if len(curr_fc_keyf_data):
                for keyf_data in curr_fc_keyf_data:
                    key_co = keyf_data[0], keyf_data[1]
                    if key_co[0] < start or key_co[0] > end:
                        new_key = fcurve.keyframe_points.insert(key_co[0], key_co[1])
                        set_keyf_data(new_key, keyf_data)
                
                
#   Utils Constraints
def get_active_child_of_cns(bone):
    constraint = None
    bparent_name = ""
    parent_type = ""
    valid_constraint = True

    if len(bone.constraints) > 0:
        for c in bone.constraints:
            if not c.mute and c.influence > 0.5 and c.type == 'CHILD_OF':
                if c.target:
                    if c.target.type == 'ARMATURE':# bone
                        bparent_name = c.subtarget
                        parent_type = "bone"
                        constraint = c
                    else:# object
                        bparent_name = c.target.name
                        parent_type = "object"
                        constraint = c

    if constraint:
        if parent_type == "bone":
            if bparent_name == "":
                valid_constraint = False

    return constraint, bparent_name, parent_type, valid_constraint

    
#   Utils Maths
def compare_mat(mat1, mat2, prec):
    for i in range(0,4):
        for j in range(0,4):
            if round(mat1[i][j], prec) != round(mat2[i][j], prec):
                return False
    return True
    
    
def look_at(tar_vec, up_vec=(0, 1, 0)):
    tar_vec = tar_vec.normalized()
    up_vec = up_vec.normalized()

    right = Vector((
        tar_vec[1] * up_vec[2] - tar_vec[2] * up_vec[1],
        tar_vec[2] * up_vec[0] - tar_vec[0] * up_vec[2],
        tar_vec[0] * up_vec[1] - tar_vec[1] * up_vec[0]
    ))
    right = right.normalized()

    forward = Vector((
        right[1] * tar_vec[2] - right[2] * tar_vec[1],
        right[2] * tar_vec[0] - right[0] * tar_vec[2],
        right[0] * tar_vec[1] - right[1] * tar_vec[0]
    ))

    rotation_matrix = Matrix((
        [right[0], tar_vec[0], forward[0], 0],
        [right[1], tar_vec[1], forward[1], 0],
        [right[2], tar_vec[2], forward[2], 0],
        [0, 0, 0, 1]
    ))
    
    return rotation_matrix
    
    
def project_point_onto_plane(q, p, n):
    n = n.normalized()
    return q - ((q - p).dot(n)) * n


def get_pose_matrix_in_other_space(mat, pose_bone):
    rest = pose_bone.bone.matrix_local.copy()
    rest_inv = rest.inverted()
    par_mat = Matrix()
    par_inv = Matrix()
    par_rest = Matrix()
    
    # bone parent case
    if pose_bone.parent and pose_bone.bone.use_inherit_rotation:
        par_mat = pose_bone.parent.matrix.copy()
        par_inv = par_mat.inverted()
        par_rest = pose_bone.parent.bone.matrix_local.copy()
    # bone parent as constraint case
    elif len(pose_bone.constraints):
        for cns in pose_bone.constraints:
            if cns.type != 'ARMATURE':
                continue
            for tar in cns.targets:
                if tar.subtarget != '':
                    if tar.weight > 0.5:# not ideal, but take the bone as parent if influence is above average
                        par_bone = get_pose_bone(tar.subtarget)
                        par_mat = par_bone.matrix.copy()
                        par_inv = par_mat.inverted()
                        par_rest = par_bone.bone.matrix_local.copy()
                        break

    smat = rest_inv @ (par_rest @ (par_inv @ mat))

    return smat
    
    
def _rotate_point(point_loc, angle, axis, origin):
    # rotate the point_loc (vector 3) around the "axis" (vector 3) 
    # for the angle value (radians)
    # around the origin (vector 3)
    rot_mat = Matrix.Rotation(angle, 4, axis.normalized())
    loc = point_loc.copy()
    loc = loc - origin
    point_mat = Matrix.Translation(loc).to_4x4()
    point_mat_rotated = rot_mat @ point_mat
    loc, rot, scale = point_mat_rotated.decompose()
    loc = loc + origin
    return loc    
    
 
#   Utils Props
def set_prop_setting(node, prop_name, setting, value):
    if bpy.app.version >= (3,0,0):
        ui_data = node.id_properties_ui(prop_name)
        if setting == 'default':
            ui_data.update(default=value)
        elif setting == 'min':
            ui_data.update(min=value)
        elif setting == 'max':
            ui_data.update(max=value)     
        elif setting == 'soft_min':
            ui_data.update(soft_min=value)
        elif setting == 'soft_max':
            ui_data.update(soft_max=value)
        elif setting == 'description':
            ui_data.update(description=value)
            
    else:
        if not "_RNA_UI" in node.keys():
            node["_RNA_UI"] = {}   
        node['_RNA_UI'][prop_name][setting] = value
        

def create_custom_prop(node=None, prop_name="", prop_val=1.0, prop_min=0.0, prop_max=1.0, prop_description="", soft_min=None, soft_max=None, default=None):
    if soft_min == None:
        soft_min = prop_min
    if soft_max == None:
        soft_max = prop_max
    
    if bpy.app.version < (3,0,0):
        if not "_RNA_UI" in node.keys():
            node["_RNA_UI"] = {}    
    
    node[prop_name] = prop_val    
    
    if default == None:
        default = prop_val
    
    if bpy.app.version < (3,0,0):
        node["_RNA_UI"][prop_name] = {'use_soft_limits':True, 'min': prop_min, 'max': prop_max, 'description': prop_description, 'soft_min':soft_min, 'soft_max':soft_max, 'default':default}
    else:     
        if type(prop_val) != str:#string props have no min, max, soft min, soft max
            set_prop_setting(node, prop_name, 'min', prop_min)
            set_prop_setting(node, prop_name, 'max', prop_max)
            set_prop_setting(node, prop_name, 'soft_min', soft_min)
            set_prop_setting(node, prop_name, 'soft_max', soft_max)
        
        set_prop_setting(node, prop_name, 'description', prop_description)        
        set_prop_setting(node, prop_name, 'default', default)
        
    # set as overridable
    node.property_overridable_library_set('["'+prop_name+'"]', True)
    

#   Utils Objects
def get_object(name):
    return bpy.data.objects.get(name)
    
    
def hide_object(obj_to_set):
    try:# object may not be in current view layer
        obj_to_set.hide_set(True)
        obj_to_set.hide_viewport = True
    except:
        pass
        
        
def unhide_object(obj_to_set):
    # we can only operate on the object if it's in the active view layer...
    try:
        obj_to_set.hide_set(False)
        obj_to_set.hide_viewport = False
    except:
        print("Could not reveal object:", obj_to_set.name)
        
        
def set_active_object(object_name):
     bpy.context.view_layer.objects.active = bpy.data.objects[object_name]
     bpy.data.objects[object_name].select_set(state=1)

     
def is_object_arp(object):
    if object.type == 'ARMATURE':
        if object.pose.bones.get('c_pos') != None:
            return True
            

#   Utils layers
def search_layer_collection(layerColl, collName):
    # Recursivly transverse layer_collection for a particular name
    found = None
    if (layerColl.name == collName):
        return layerColl
    for layer in layerColl.children:
        found = search_layer_collection(layer, collName)
        if found:
            return found



# OPERATOR FUNCTIONS  ------------------------------------------------------------------
def get_pinned_props_list(rig):
    current_pinned_string = rig.data["arp_pinned_props"]
    return current_pinned_string.split(',')
    
    
def _childof_keyer(pb):  
    for cns in pb.constraints:    
        if not cns.enabled:
            continue
        if cns.type == 'CHILD_OF':
            cns.keyframe_insert(data_path='influence')


def _childof_switcher(self):
    rig = bpy.context.active_object
    pb = bpy.context.selected_pose_bones[0]
    mat_prev = pb.matrix.copy()
    scn = bpy.context.scene
    
    def disable_cns(cns):
        if cns.influence != 0.0:
            
            parent_type = 'bone' if cns.subtarget else 'object'
            parent_name = cns.subtarget if parent_type == 'bone' else cns.target.name
            
            # set influence
            cns.influence = 0.0
            
            # snap
            if parent_type == 'bone':
                bone_parent = get_pose_bone(parent_name)             
                pb.matrix = mat_prev                
                
            elif parent_type == 'object':
                obj_par = get_object(parent_name)
                pb.matrix = cns.inverse_matrix.inverted() @ obj_par.matrix_world.inverted() @ pb.matrix
                
            # auto keyframe
            if scn.tool_settings.use_keyframe_insert_auto:
                keyframe_pb_transforms(pb)
                cns.keyframe_insert(data_path='influence')
                
            
    def enable_cns(cns):
        debug = False
        
        if cns.influence != 1.0:
            if debug:
                print("enable constraint:", cns.name)
            parent_type = 'bone' if cns.subtarget else 'object'
            parent_name = cns.subtarget if parent_type == 'bone' else cns.target.name            
            
            if debug:
                print("MAT INIT")
                mat_init = pb.matrix.copy()                
                print(mat_init)
                
            # set influence
            cns.influence = 1.0
         
            update_transform() 
            
            # snap
            if parent_type == 'bone':
                bone_parent = get_pose_bone(parent_name)
                pb.matrix = cns.inverse_matrix.inverted() @ bone_parent.matrix.inverted() @ mat_prev
                
                update_transform()
                
                if debug:
                    print("MAT POST")
                    print(pb.matrix)          
                
            elif parent_type == 'object':
                if debug:
                    print("  object type")
                obj_par = get_object(parent_name)
                pb.matrix = cns.inverse_matrix.inverted() @ obj_par.matrix_world.inverted() @ mat_prev#pb.matrix
                
            # auto keyframe
            if scn.tool_settings.use_keyframe_insert_auto:
                keyframe_pb_transforms(pb)
                cns.keyframe_insert(data_path='influence')
                
    
    for cns in pb.constraints: 
        if not cns.enabled:
            continue
        if cns.type != 'CHILD_OF':
            continue
        if cns.name != self.child_of_cns:            
            disable_cns(cns)  

    for cns in pb.constraints:
        if not cns.enabled:
            continue
        if cns.type != 'CHILD_OF':
            continue
        if cns.name == self.child_of_cns:
            enable_cns(cns)
    

#   Rig Layers
def _export_layers_sets(self):
    scn = bpy.context.scene
    rig = bpy.context.active_object
    
    filepath = self.filepath
    
    if not filepath.endswith(".py"):
        filepath += ".py"

    file = open(filepath, "w", encoding="utf8", newline="\n")
    layers_set_dict = {}
    
    """
    name: string
    layers: Bool list
    objects_set: CollectionProp[object_item(pointer object)]
    collection: Pointer(Collection)    
    bones: String
    """
    
    # fetch data
    for layerset in rig.layers_sets:
        layer_dict = {}
        
        # name
        layer_dict['name'] = layerset.name
        
        # bones collections/layers
        if bpy.app.version >= (4,0,0):          
            bones_collec_names = []
            for item in layerset.bonecollections_set:
                for col in get_armature_collections(rig):
                    if 'collec_id' in col.keys():
                        if col['collec_id'] == item.collec_id:
                            bones_collec_names.append(col.name)
            
            layer_dict['bonecollections_set'] = bones_collec_names
            
        else:
            layer_dict['layers'] = [i for i in layerset.layers]
        
        # objects
        objects_names = []
        for obj_i in layerset.objects_set:
            obj = obj_i.object_item
            if obj != None:
                objects_names.append(obj.name)
            
        layer_dict['objects_set'] = objects_names
        
        # collection
        collec_name = ''
        if layerset.collection != None:
            collec_name = layerset.collection.name
            
        layer_dict['collection'] = collec_name
        
        # bones
        layer_dict['bones'] = layerset.bones        
        
        # set dict    
        layers_set_dict[layerset.name] = layer_dict
    
    # write file
    file.write(str(layers_set_dict))

    # close file
    file.close()   
    
    
def _import_layers_sets(self):
    filepath = self.filepath
    scn = bpy.context.scene
    rig = bpy.context.active_object   
    
    # read file
    file = open(filepath, 'r') if sys.version_info >= (3, 11) else open(filepath, 'rU')
    file_lines = file.readlines()
    dict_str = str(file_lines[0])
    file.close()
    
    # import data
    layers_set_dict = ast.literal_eval(dict_str)     
    
    for layer_name in layers_set_dict:
      
        layerset = rig.layers_sets.add()
        
        # name
        layerset.name = layer_name
        
        # bones collections/layers
        if bpy.app.version >= (4,0,0):
            bones_col_names = layers_set_dict[layer_name]['bonecollections_set']
            if len(bones_col_names):
                for collec_name in bones_col_names:
                    col = get_armature_collections(rig).get(collec_name)
                    if col:                       
                        item = layerset.bonecollections_set.add()
                        col_id = None
                        if 'collec_id' in col.keys():
                            col_id = col['collec_id']
                        else:
                            col_id = generate_collec_id(col.name)
                        item.collec_id = col_id
        else:
            layerset.layers = layers_set_dict[layer_name]['layers']
        
        # objects
        objects_set = layers_set_dict[layer_name]['objects_set']
        if len(objects_set):
            for name in objects_set:
                if get_object(name):
                    obj_i = layerset.objects_set.add()
                    obj_i.object_item = get_object(name)
                    
        # object collection
        collec_name = layers_set_dict[layer_name]['collection']
        if collec_name != '':
            collec = bpy.data.collections.get(collec_name)
            if collec:
                layerset.collection = collec
                
        # bones
        layerset.bones = layers_set_dict[layer_name]['bones']
            

def draw_layer_set_edit(self, context):
    rig = context.active_object 
    
    if len(rig.layers_sets) == 0:
        return
        
    current_set = rig.layers_sets[rig.layers_sets_idx]
    
    layout = self.layout
    
    # bones layers/collection
    if bpy.app.version >= (4,0,0):
        layout.label(text='Bones Collections:')  
        col = layout.column(align=True)
        row = col.row(align=True)
        row.prop_search(current_set, 'collection_to_add', rig.data, 'collections', text='')#prop_search(scn, "arp_eyeball_name_right", bpy.data, "objects", text="")
        row.operator("arp.layers_sets_add_collection", text="", icon="ADD")
        
        col.separator()
        
        # display current bone collections in set
        if len(current_set.bonecollections_set):
            for item in current_set.bonecollections_set:
                for collec in get_armature_collections(rig):
                    if 'collec_id' in collec.keys():
                        if item.collec_id == collec['collec_id']:
                            row2 = col.row(align=True)
                            op = row2.operator('arp.delete_bone_collec', text='', icon = 'X')
                            op.collec_id = item.collec_id
                            row2.label(text=collec.name)
                            continue
        else:
            col.label(text='No bones collections in this set')
    
    else:
        layout.label(text='Layers:')
        col = layout.column(align=True)   
        col.prop(current_set, 'layers', text='')
   
    layout.separator()  
    
    # bones
    bones_list = ast.literal_eval(current_set.bones)
    len_bones = str(len(bones_list))
    col = layout.column()
    col.label(text='Bones:')
    row = col.row(align=True)
    row.operator("arp.layers_sets_add_bones", text="Add Selected Bones ("+len_bones+")")
    row.operator("arp.layers_sets_remove_bones", text="", icon="PANEL_CLOSE")
    col.prop(current_set, "show_bones", text="", icon="HIDE_OFF")
    
    if current_set.show_bones:
        col = layout.column(align=True)
        if len(bones_list):
            for bname in bones_list:
                col.label(text=bname)
        else:
            col.label(text="No bones in this set")
            
    # collection
    col = layout.column()
    col.label(text='Objects Collection:')
    col.prop(current_set, 'collection', text='')
    
    # objects
    col.separator()
    col.label(text='Objects:')
    row = col.row(align=True)
    row.prop(current_set, "object_to_add", text='')
    row.operator("arp.layers_sets_add_object", text="", icon="ADD")
   
    layout.operator("arp.layers_sets_clear_objects", text="Remove All Objects")
    layout.prop(current_set, "show_objects", text="", icon="HIDE_OFF")
    
    if current_set.show_objects:
        col = layout.column(align=True)
        if len(current_set.objects_set):
            for obji in current_set.objects_set:
                col.label(text=obji.object_item.name)
        else:
            col.label(text="No objects in this set")
    
    layout.separator()

    
def set_layer_vis(self, state):
    rig = bpy.context.active_object
    scn = bpy.context.scene
    
    if rig == None:# nothing selected
        return
        
    if rig.type != 'ARMATURE':
        return
    
    # set armature bones collections/layers visibility   
    if bpy.app.version >= (4,0,0):
        for item in self.bonecollections_set:
            for collec in get_armature_collections(rig):
                if 'collec_id' in collec.keys():
                    if item.collec_id == collec['collec_id']:
                        if collec.is_visible != state:# ultimate check necessary to prevent an update failure when updating collec viz + motion trails 
                            collec.is_visible = not collec.is_visible

    else:
        for i, lay in enumerate(self.layers):
            if lay:
                rig.data.layers[i] = state
        
    # set bones visibility
    bones_names = ast.literal_eval(self.bones)
    
    for bname in bones_names:
        if bpy.context.mode == "EDIT_ARMATURE":
            b = get_edit_bone(bname)
            if b:
                b.hide = not state
            
        elif bpy.context.mode == "POSE" or bpy.context.mode == "OBJECT":
            if bpy.app.version >= (5,0,0):
                pb = get_pose_bone(bname)
                if pb:
                    pb.hide = not state
            else:
                b = get_data_bone(bname)
                if b:
                    b.hide = not state
            
    
    # set object collection visibility
    if self.collection != None: 
        # hide at collection level
        self.collection.hide_viewport = not state
        
        if scn.arp_layers_set_render:
            self.collection.hide_render = not state
                
        # hide at view layer level
        try:
            layer_col = search_layer_collection(bpy.context.view_layer.layer_collection, self.collection.name)              
            layer_col.hide_viewport = not state
            
            if scn.arp_layers_set_render:
                layer_col.hide_render = not state
            
        except:
            pass
            
    # set objects visibility
    for obji in self.objects_set:
        obj = obji.object_item
        if state == True:
            unhide_object(obj)
            
            if scn.arp_layers_set_render:
                obj.hide_render = False
        else:
            hide_object(obj)
            
            if scn.arp_layers_set_render:
                obj.hide_render = True
    

def _add_layer_set(self):
    rig = bpy.context.active_object
    
    new_set = rig.layers_sets.add()
    new_set.name = 'LayerSet'    

    rig.layers_sets_idx = len(rig.layers_sets)-1    

        
def _remove_layer_set(self):
    rig = bpy.context.active_object
    
    rig.layers_sets.remove(rig.layers_sets_idx)
    
    if rig.layers_sets_idx > len(rig.layers_sets)-1:
        rig.layers_sets_idx = len(rig.layers_sets)-1
        

def _clear_root_motion(self):
    print("Clear root motion...")
    
    time_start = time.time()
    
    rig = get_object(bpy.context.active_object.name)
    action = rig.animation_data.action
    
    c_traj_name = 'c_traj'
    c_traj_pb = get_pose_bone(c_traj_name)
    
    bones_parented = []
    bones_constrained = []# only ChildOf is supported for now
    c_traj_mats = {}
    bones_mats = {}
    
    # Get all bones parented/constrained to c_traj
    head_scale_fix_name = 'head_scale_fix'
    
    for pb in rig.pose.bones:
        # only controllers or custom bones.
        if pb.name.startswith('c_') or 'cc' in pb.bone.keys() or pb.name == head_scale_fix_name+get_bone_side(pb.name):
            
            # special case, the head_scale_fix bone is both parented and constrained to c_traj in case Head Lock is disabled, 
            # > map to c_head.x
            if pb.name.startswith(head_scale_fix_name):
                for cns in pb.constraints:
                    if cns.type == 'CHILD_OF' and cns.influence > 0.0 and cns.enabled:
                        if cns.target == rig and cns.subtarget == c_traj_name:
                            bones_parented.append('c_head'+get_bone_side(pb.name))
                
            elif pb.bone.parent == get_data_bone(c_traj_name):
                # make sure c_root_masters is always first in the line, to evaluate the next dependent hierarchy properly
                if pb.name == 'c_root_master'+get_bone_side(pb.name):
                    bones_parented.insert(0, pb.name)
                else:
                    bones_parented.append(pb.name)
            else:
                for cns in pb.constraints:
                    if cns.type == 'CHILD_OF' and cns.influence > 0.0 and cns.enabled:
                        if cns.target == rig and cns.subtarget == c_traj_name: 
                            if not pb.name in bones_constrained:
                                bones_constrained.append(pb.name)
    
    
    print('Storing matrices...')
    
    for f in range(self.frame_start, self.frame_end+1):
        bpy.context.scene.frame_set(f)

        c_traj_mats[f] = c_traj_pb.matrix.copy()
        
        for pbname in bones_parented + bones_constrained:
            pb = get_pose_bone(pbname)
            pb_mat = pb.matrix.copy()
            if not pbname in bones_mats:
                bones_mats[pbname] = {f: pb_mat}
            else:
                dico = bones_mats[pbname]
                dico[f] = pb_mat
                bones_mats[pbname] = dico
                
    prep_time = round(time.time() - time_start, 2)
    print('Prep time', prep_time)    
    time_start = time.time()
    
    print("Reset and bake...")
    keyframes = {}
    euler_prevs = {}
    quat_prevs = {}
    
    for f in range(self.frame_start, self.frame_end+1):
        bpy.context.scene.frame_set(f)
     
        zero_out_pb(c_traj_pb)
        update_transform()
        
        # store keyframe
        #keyframe_pb_transforms(c_traj_pb, loc=True, rot=True, scale=False)
        store_loc_key(c_traj_pb, f, keyframes)
        store_rot_key(c_traj_pb, f, euler_prevs, quat_prevs, keyframes)   
        
        # restore other mats
        for pbname in bones_mats:
            pb = get_pose_bone(pbname)
            dico = bones_mats[pbname]
            snap_bone_matrix(pb, dico[f], updt=False)
            #if self.force_full_update:
            if len(bones_parented) > 1 and pbname == 'c_root_master'+get_bone_side(pbname):# TODO: to make it right, should be necessary to build a correct hierarchy tree and update transforms based on it
                bpy.context.view_layer.update()
            
        #if self.force_full_update:
        bpy.context.view_layer.update()
        #update_transform()

        for pbname in bones_mats:
            pb = get_pose_bone(pbname)
            #keyframe_pb_transforms(pb, loc=True, rot=True, scale=True)
            store_loc_key(pb, f, keyframes)
            store_rot_key(pb, f, euler_prevs, quat_prevs, keyframes)
            
                   
    # Add keyframes
    insert_keyframes(action, keyframes, start=self.frame_start, end=self.frame_end)
    
    end_time = round(time.time() - time_start, 2)
    print('Bake time', end_time)
    print("Root motion cleared.")

  
def _extract_root_motion(self):
    print("Extract root motion...")
    bpy.ops.object.mode_set(mode='POSE')
    time_start = time.time()
    
    c_traj_name = 'c_traj'
    c_traj_pb = get_pose_bone(c_traj_name)
    
    c_traj_x_offset = 0.0
    c_traj_y_offset = 0.0
    c_traj_z_offset = 0.0
    
    rig = get_object(bpy.context.active_object.name)
    action = rig.animation_data.action
    bones_parented = []
    bones_constrained = []# only ChildOf is supported for now
    
    root_name = 'c_root_master.x' if self.root_type == 'ROOT_MASTER' else 'c_root.x'
    c_root_pb = get_pose_bone(root_name)
    c_root_mats = {}    
    c_traj_mats = {}
    bones_mats = {}
    
    # Get all bones parented/constrained to c_traj
    head_scale_fix_name = 'head_scale_fix'
    
    for pb in rig.pose.bones:
        # only controllers or custom bones.
        if pb.name.startswith('c_') or 'cc' in pb.bone.keys() or pb.name == head_scale_fix_name+get_bone_side(pb.name):
            
            # special case, the head_scale_fix bone is both parented and constrained to c_traj in case Head Lock is disabled, 
            # > map to c_head.x
            if pb.name.startswith(head_scale_fix_name):
                for cns in pb.constraints:
                    if cns.type == 'CHILD_OF' and cns.influence > 0.0 and cns.enabled:
                        if cns.target == rig and cns.subtarget == c_traj_name:
                            bones_parented.append('c_head'+get_bone_side(pb.name))
                
            elif pb.bone.parent == get_data_bone(c_traj_name):
                # make sure c_root_masters is always first in the line, to evaluate the next dependent hierarchy properly
                if pb.name == 'c_root_master'+get_bone_side(pb.name):
                    bones_parented.insert(0, pb.name)
                else:
                    bones_parented.append(pb.name)
            else:
                for cns in pb.constraints:
                    if cns.type == 'CHILD_OF' and cns.influence > 0.0 and cns.enabled:
                        if cns.target == rig and cns.subtarget == c_traj_name: 
                            if not pb.name in bones_constrained:
                                bones_constrained.append(pb.name)
    

        
    print('bones_parented', bones_parented)
    print('bones_constrained', bones_constrained)
    print('Storing matrices...')
    
    for f in range(self.frame_start, self.frame_end+1):
        bpy.context.scene.frame_set(f)
        
        c_root_mats[f] = get_pose_bone(root_name).matrix.copy()
        c_traj_mats[f] = c_traj_pb.matrix.copy()
        
        if f == self.frame_start:
            c_traj_x_offset = c_traj_pb.matrix.decompose()[0][0] - c_root_pb.matrix.decompose()[0][0]
            c_traj_y_offset = c_traj_pb.matrix.decompose()[0][1] - c_root_pb.matrix.decompose()[0][1]
            c_traj_z_offset = c_traj_pb.matrix.decompose()[0][2] - c_root_pb.matrix.decompose()[0][2]
        
        for pbname in bones_parented + bones_constrained:
            pb = get_pose_bone(pbname)
            pb_mat = pb.matrix.copy()
            if not pbname in bones_mats:
                bones_mats[pbname] = {f: pb_mat}
            else:
                dico = bones_mats[pbname]
                dico[f] = pb_mat
                bones_mats[pbname] = dico
                
    
    prep_time = round(time.time() - time_start, 2)
    print('Prep time', prep_time)
    
    time_start = time.time()
    
    print("Extract and bake...")
    keyframes = {}
    euler_prevs = {}
    quat_prevs = {}
    
    for f in range(self.frame_start, self.frame_end+1):
        bpy.context.scene.frame_set(f)
        
        # restore original c_traj transforms
        c_traj_pb.matrix = c_traj_mats[f]
        update_transform()
        
        # extract root location and rotation
        root_loc = c_root_mats[f].decompose()[0]
        traj_loc, traj_rot, traj_scale = c_traj_pb.matrix.decompose()
        # loc
        loc = root_loc
        
        if self.loc_x == False:
            loc[0] = traj_loc[0]
        else:
            if self.loc_x_offset:
                loc[0] += c_traj_x_offset
                
        if self.loc_y == False:
            loc[1] = traj_loc[1]
        else:
            if self.loc_y_offset:
                loc[1] += c_traj_y_offset
                
        if self.loc_z == False:
            loc[2] = traj_loc[2]
        else:
            if self.loc_z_offset:
                loc[2] += c_traj_z_offset
        
        # rot
        rot = traj_rot
        if self.rotation:
            target_vec = None            
            if 'X' in self.forward_axis:
                target_vec = c_root_pb.x_axis if self.root_type == 'ROOT_MASTER' else -c_root_pb.x_axis
            elif 'Y' in self.forward_axis:
                target_vec = c_root_pb.y_axis if self.root_type == 'ROOT_MASTER' else -c_root_pb.y_axis
            elif 'Z' in self.forward_axis:
                target_vec = c_root_pb.z_axis if self.root_type == 'ROOT_MASTER' else -c_root_pb.z_axis
           
            if '-' in self.forward_axis:
                target_vec *= -1.0
                
            target_vec[2] = 0.0
            rot_mat = look_at(target_vec, up_vec=Vector((0,0,1)))
            rot = rot_mat.decompose()[1]
        
        # apply
        mat_def = Matrix.LocRotScale(loc, rot, traj_scale)
        c_traj_pb.matrix = mat_def
        update_transform()
        
        # store keyframe
        #keyframe_pb_transforms(c_traj_pb, loc=True, rot=True, scale=False)
        store_loc_key(c_traj_pb, f, keyframes)
        store_rot_key(c_traj_pb, f, euler_prevs, quat_prevs, keyframes)       
        
        # restore other mats
        for pbname in bones_mats:
            pb = get_pose_bone(pbname)
            dico = bones_mats[pbname]
            snap_bone_matrix(pb, dico[f], updt=False)
            #if self.force_full_update:
            if len(bones_parented) > 1 and pbname == 'c_root_master'+get_bone_side(pbname):# TODO: to make it right, should be necessary to build a correct hierarchy tree and update transforms based on it
                bpy.context.view_layer.update()
               
        #if self.force_full_update:
        #update_transform()
        bpy.context.view_layer.update()
        
        # store keyframe        
        for pbname in bones_mats:
            pb = get_pose_bone(pbname)
            #keyframe_pb_transforms(pb, loc=True, rot=True, scale=False)
            store_loc_key(pb, f, keyframes)            
            store_rot_key(pb, f, euler_prevs, quat_prevs, keyframes)
            
            
    # Add keyframes
    insert_keyframes(action, keyframes, start=self.frame_start, end=self.frame_end)
    
    end_time = round(time.time() - time_start, 2)
    print('Bake time', end_time)
    
    print('Root motion extracted.')
    
    
# Snap Rev Spine
def snap_spine_rev_to_fwd(side):
    print('Snap Rev to Fwd')
    c_root_master_pb = get_pose_bone('c_root_master'+side)
    c_chest_pb = get_pose_bone('c_chest'+side)
    zero_out_pb(c_chest_pb)
    
    # snap
    aligned_first = False
    
    for i in reversed(range(0, 65)):
        stri = '%02d' % i
        stri_nxt = '%02d' % (i+1)
        c_spine_name = 'c_spine_'+stri+side if i != 0 else 'root_snap'+side
        c_spine_nxt_name = 'c_spine_'+stri_nxt+side
        c_spine_rev_name = 'c_spine_'+stri+'_rev'+side if i != 0 else 'c_root_rev'+side
        c_spine = get_pose_bone(c_spine_name)
        c_spine_rev = get_pose_bone(c_spine_rev_name)
        #c_spine_nxt = get_pose_bone(c_spine_nxt_name)
        c_spine_snap = get_pose_bone('spine_snap_'+stri+side)
        
        if c_spine == None or c_spine_rev == None:
            continue
        
        # since the rev ctrls are shifted by one unit above,
        # we need to snap the position to the next spine, while keeping the rot and scale transforms
        # of the current spine
        target_mat = None
        #if c_spine_nxt and i != 0:
        if c_spine_snap and i != 0:       
            target_mat = c_spine_snap.matrix.copy()
        else:
            target_mat = c_spine.matrix.copy()
            
        c_spine_rev.matrix = target_mat
            
        update_transform()      
        
        if aligned_first == False:# align the spine master right after the first reversed spine bone
            aligned_first = True            
            c_spine_master_rev_name = 'c_spine_master_rev'+side
            c_spine_master_rev = get_pose_bone(c_spine_master_rev_name)
            if c_spine_master_rev:
                c_root_name = 'root_snap'+side
                c_root = get_pose_bone(c_root_name)                
                c_spine_master_rev.matrix = c_root.matrix.copy()
                update_transform()       
                
                spine_stretchy = get_pose_bone('spine_stretchy'+side)
                if spine_stretchy:
                    # Offset the c_spine_master_rev by the current vector to match the stretch length
                    spine_stretchy_rev = get_pose_bone('spine_stretchy_rev'+side)
                    
                    diff = (spine_stretchy.length/spine_stretchy_rev.length)
                    spine_stretchy_rev_loc = spine_stretchy_rev.matrix.decompose()[0]
                    c_spine_master_rev_loc = c_spine_master_rev.matrix.decompose()[0]
                    
                    vec_rev = (c_spine_master_rev_loc - spine_stretchy_rev_loc)                    
                    mat_transl = Matrix.Translation(vec_rev*diff).to_4x4()
                    loc, r, s = (mat_transl @ spine_stretchy_rev.matrix).decompose()
                    rot, sca = c_spine_master_rev.matrix.decompose()[1], c_spine_master_rev.matrix.decompose()[2]
                    mat_def = Matrix.LocRotScale(loc, rot, sca)
                    c_spine_master_rev.matrix = mat_def
                    update_transform()
    
        
    # switch
    c_root_master_pb['reverse_spine'] = 1.0
    update_transform()
    
    
def snap_spine_fwd_to_rev(side):
    print('Snap Fwd to Rev')
    c_root_master_pb = get_pose_bone('c_root_master'+side)
    c_spine_master_pb = get_pose_bone('c_spine_master'+side)
    first_spine = get_pose_bone('c_spine_01'+side)
    
    # reset c_spine_master
    if c_spine_master_pb:
        zero_out_pb(c_spine_master_pb)
    zero_out_pb(first_spine)
    update_transform()
    
    #   get tip spine
    last_spine_rev_name = ''
    last_spine_rev = None
    last_spine_idx = 3
    for i in reversed(range(1, 64)):
        stri = '%02d' % i
        c_spine_name = 'c_spine_'+stri+'_rev'+side
        c_spine = get_pose_bone(c_spine_name)
        if c_spine:
            last_spine_rev_name = c_spine_name
            last_spine_rev = get_pose_bone(last_spine_rev_name)
            last_spine_idx = i
            break
    
    if c_spine_master_pb:
        # Offset the c_spine_master by the current vector to match the stretch length
        # Another way would be to move c_root_master first. TODO, add it as an option
        
        first_spine_rev_name = 'spine_01_rev_snap'+side
        first_spine_rev = get_pose_bone(first_spine_rev_name)
        c_spine_master_rev = get_pose_bone('c_spine_master_rev'+side)
        
        #   compute offset  
        last_spine_rev_loc = last_spine_rev.matrix.decompose()[0]
        first_spine_rev_loc = first_spine_rev.matrix.decompose()[0]
        c_spine_master_rev_loc = c_spine_master_rev.matrix.decompose()[0]
        c_spine_master_pb_loc = c_spine_master_pb.matrix.decompose()[0]
        first_spine_loc = first_spine.matrix.decompose()[0]
        
        vec_rev = (last_spine_rev_loc - c_spine_master_rev_loc)
        vec_fwd = (c_spine_master_pb_loc - first_spine_loc)        
        diff = (vec_rev.magnitude / vec_fwd.magnitude)-1
        mat_transl = Matrix.Translation(vec_fwd*diff).to_4x4()
        c_spine_master_pb.matrix = mat_transl @ c_spine_master_pb.matrix
        update_transform()

    
    # snap spine bones
    for i in range(0, last_spine_idx+1):
        stri = '%02d' % i
        stri_prev = '%02d' % (i-1)
        c_spine_name = 'c_spine_'+stri+side if i != 0 else 'c_root'+side
        c_spine_rev_name = 'spine_'+stri+'_rev_snap'+side
        c_spine_rev_prev_name = 'c_spine_'+stri_prev+'_rev'+side
        
        if i == 0:
            c_spine_rev_name = 'root_rev_snap'+side
        if i == last_spine_idx:
            c_spine_rev_name = 'c_chest'+side
        c_spine = get_pose_bone(c_spine_name)
        c_spine_rev = get_pose_bone(c_spine_rev_name)
        c_spine_rev_prev = get_pose_bone(c_spine_rev_prev_name)
        
        if c_spine == None or c_spine_rev == None:
            continue
  
        c_spine.matrix = c_spine_rev.matrix.copy()
            
        update_transform()       
    
    # switch
    c_root_master_pb['reverse_spine'] = 0.0
    update_transform()


#   IK FK toes
def ik_to_fk_toe(root_toe, side):

    toe_type = None
    rig = bpy.context.active_object

    for i in fingers_type_list:
        if i in root_toe.name:
            toe_type = i
            break

    ik_target_name = "c_toes_"+toe_type+"_ik_tar"+side

    ik_target = get_pose_bone(ik_target_name)
    if ik_target == None:
        return

    ik_pole_name = "c_toes_"+toe_type+"_ik_pole"+side
    ik_pole = get_pose_bone(ik_pole_name)
    if ik_pole == None:
        return

    foot_b = get_data_bone("foot_ref"+side)

    toes_ik_pole_distance = 1.0
    ik_dist_prop_name = 'ik_pole_distance'
    if ik_dist_prop_name in foot_b.keys():
        toes_ik_pole_distance = foot_b[ik_dist_prop_name]

    # Snap IK target
    #   constraint support
    #constraint, bparent_name, parent_type, valid_constraint = get_active_child_of_cns(ik_target)

    last_idx = '2' if toe_type == 'thumb' else '3'
    finger3_fk = get_pose_bone("c_toes_"+toe_type+last_idx+side)
    
    # disable constraints
    cns_states = []
    for cns in ik_target.constraints:
        cns_states.append(cns.enabled)
        cns.enabled = False
        
    update_transform()
    
    # snap (no cns)
    ik_target.matrix = finger3_fk.matrix.copy()
    update_transform()
    mat_no_cns = ik_target.matrix.copy()
    
    # enable constraints
    for ci, cns in enumerate(ik_target.constraints):
        cns.enabled = cns_states[ci]
    
    update_transform()
    
    # compensate constraints offset
    mat_cns = ik_target.matrix.copy()
    mat_diff = mat_cns.inverted() @ mat_no_cns
    ik_target.matrix = mat_no_cns @ mat_diff
    
    update_transform()
  

    # Snap IK pole
    fk_toes = ["c_toes_"+toe_type+"1"+side, "c_toes_"+toe_type+"2"+side]
    ik_toes = ["toes_"+toe_type+"1_ik"+side, "toes_"+toe_type+"2_ik"+side]  

    
    phal2 = get_pose_bone(fk_toes[1])
    #   constraint support
    pole_cns, bpar_name, par_type, valid_cns = get_active_child_of_cns(ik_pole)

    if pole_cns and valid_cns:
        bone_parent = get_pose_bone(bpar_name)
        ik_pole.matrix = bone_parent.matrix_channel.inverted() @ Matrix.Translation((phal2.z_axis.normalized() * phal2.length * 1.3 * toes_ik_pole_distance)) @ phal2.matrix
    else:
        ik_pole.matrix = Matrix.Translation((phal2.z_axis.normalized() * phal2.length * 1.3 * toes_ik_pole_distance)) @ phal2.matrix

    ik_pole.rotation_euler = [0,0,0]

    update_transform()
    
    phal1_fk = get_pose_bone(fk_toes[0])
    phal2_fk = get_pose_bone(fk_toes[1])
    phal1_ik = get_pose_bone(ik_toes[0])
    phal2_ik = get_pose_bone(ik_toes[1])
    
    compensate_ik_pole_position(phal1_fk, phal2_fk, phal1_ik, phal2_ik, ik_pole)
    update_transform()
    '''
    pole_pos = get_ik_pole_pos(phal1_fk, phal2_fk, toes_ik_pole_distance)
    pole_mat = Matrix.Translation(pole_pos)
    snap_bone_matrix(ik_pole, pole_mat)
    '''
    
    '''
    #   phalanges
    for iter in range(0,4):
        for i, bname in enumerate(ik_toes):
            b_ik = get_pose_bone(bname)
            loc, scale = b_ik.location.copy(), b_ik.scale.copy()
            b_fk = get_pose_bone(fk_toes[i])
            b_ik.matrix = b_fk.matrix
            # restore loc and scale, only rotation for better results
            b_ik.location = loc
            b_ik.scale = scale
            # update hack
            update_transform()
    '''
    
     # Switch prop
    root_toe['ik_fk_switch'] = 0.0

    # udpate hack
    update_transform()

    #insert key if autokey enable
    if bpy.context.scene.tool_settings.use_keyframe_insert_auto:
        root_toe.keyframe_insert(data_path='["ik_fk_switch"]')

        for bname in ik_toes + fk_toes + [ik_target.name]:
            pb = get_pose_bone(bname)
            pb.keyframe_insert(data_path="location")
            if pb.rotation_mode != "QUATERNION":
                pb.keyframe_insert(data_path="rotation_euler")
            else:
                pb.keyframe_insert(data_path="rotation_quaternion")
            
            for i, j in enumerate(pb.lock_scale):
                if not j:
                    pb.keyframe_insert(data_path="scale", index=i)
    

def fk_to_ik_toe(root_toe, side):
    toe_type = None    

    for i in fingers_type_list:
        if i in root_toe.name:
            toe_type = i
            break  
    
    # snap
    fk_toes = ["c_toes_"+toe_type+"1"+side, "c_toes_"+toe_type+"2"+side, "c_toes_"+toe_type+"3"+side]
    ik_toes = ["toes_"+toe_type+"1_ik"+side, "toes_"+toe_type+"2_ik"+side, "toes_"+toe_type+"3_ik"+side]

    for i in range(0,2):
        for i, name in enumerate(fk_toes):        
            b_fk = get_pose_bone(name)
            b_ik = get_pose_bone(ik_toes[i])
            
            if i == 0:# need to compensate the first FK phalange constraint
                # disable constraints
                cns_states = []
                for cns in b_fk.constraints:
                    cns_states.append(cns.enabled)
                    cns.enabled = False
                    
                update_transform()
                
                # snap (no cns)
                b_fk.matrix = b_ik.matrix.copy()
                update_transform()
                mat_no_cns = b_fk.matrix.copy()
                
                # enable constraints
                for ci, cns in enumerate(b_fk.constraints):
                    cns.enabled = cns_states[ci]
                
                update_transform()
                
                # compensate constraints offset
                mat_cns = b_fk.matrix.copy()
                mat_diff = mat_cns.inverted() @ mat_no_cns
                b_fk.matrix = mat_no_cns @ mat_diff
                
                update_transform()
    
            else:            
                b_fk.matrix = b_ik.matrix.copy()

            # udpate hack
            update_transform()

     #switch
    root_toe['ik_fk_switch'] = 1.0

    # udpate hack
    update_transform()

    #insert key if autokey enable
    if bpy.context.scene.tool_settings.use_keyframe_insert_auto:
        root_toe.keyframe_insert(data_path='["ik_fk_switch"]')

        for bname in ik_toes + fk_toes:# + [ik_target.name]:
            pb = get_pose_bone(bname)
            pb.keyframe_insert(data_path="location")
            if pb.rotation_mode != "QUATERNION":
                pb.keyframe_insert(data_path="rotation_euler")
            else:
                pb.keyframe_insert(data_path="rotation_quaternion")
            
            for i, j in enumerate(pb.lock_scale):
                if not j:
                    pb.keyframe_insert(data_path="scale", index=i) 
                    
    
        
#   IK FK fingers
def ik_to_fk_finger(root_finger, side):    
    finger_type = None
    rig = bpy.context.active_object

    for i in fingers_type_list:
        if i in root_finger.name:
            finger_type = i
            break
            
    print('ik to fk finger '+finger_type+'...')

    ik_target_name = ''
    ik_tip = root_finger['ik_tip']
    
    if root_finger['ik_tip'] == 1:# ik1
        ik_target_name = 'c_'+finger_type+'_ik'+side        
        if get_pose_bone(ik_target_name) == None:# backward-compatibility
            root_finger['ik_tip'] = 0
            
    if root_finger['ik_tip'] == 0:# ik2
        ik_target_name = 'c_'+finger_type+'_ik2'+side

    ik_target = get_pose_bone(ik_target_name)
    if ik_target == None:
        print('missing finger ik target:', ik_target_name)
        return

    ik_pole_name = 'c_'+finger_type+'_pole'+side
    ik_pole = get_pose_bone(ik_pole_name)
    if ik_pole == None:
        print('missing finger ik pole:', ik_pole_name)
        return

    hand_b = get_data_bone('hand_ref'+side)

    fingers_ik_pole_distance = 1.0
    if 'fingers_ik_pole_distance' in hand_b.keys():
        fingers_ik_pole_distance = hand_b['fingers_ik_pole_distance']

    # Snap IK target
        # constraint support
    constraint, bparent_name, parent_type, valid_constraint = get_active_child_of_cns(ik_target)

    finger3_fk = get_pose_bone('c_'+finger_type+'3'+side)
    if constraint and valid_constraint:
        if parent_type == 'bone':
            bone_parent = get_pose_bone(bparent_name)
            ik_target.matrix = bone_parent.matrix_channel.inverted() @ finger3_fk.matrix
            update_transform()
            if root_finger['ik_tip'] == 1:
                # set head to tail position
                tail_mat = bone_parent.matrix_channel.inverted() @ Matrix.Translation((ik_target.y_axis.normalized() * ik_target.length))
                ik_target.matrix = tail_mat @ ik_target.matrix
            print('snapped', ik_target.name, 'to', finger3_fk.name)

        if parent_type == "object":
            obj = bpy.data.objects.get(bparent_name)
            ik_target.matrix = constraint.inverse_matrix.inverted() @ obj.matrix_world.inverted() @ finger3_fk.matrix
            update_transform()
            if root_finger['ik_tip'] == 1:
                # set head to tail position
                tail_mat = constraint.inverse_matrix.inverted() @ obj.matrix_world.inverted() @ Matrix.Translation((ik_target.y_axis.normalized() * ik_target.length))
                ik_target.matrix = tail_mat @ ik_target.matrix
    else:
        ik_target.matrix = finger3_fk.matrix
        update_transform()
        if root_finger['ik_tip'] == 1:
            # set head to tail position
            tail_mat = Matrix.Translation((ik_target.y_axis.normalized() * ik_target.length))
            ik_target.matrix = tail_mat @ ik_target.matrix

    update_transform()

    # Snap IK pole
    fk_fingers = ["c_"+finger_type+"1"+side, "c_"+finger_type+"2"+side, "c_"+finger_type+"3"+side]
    ik_fingers = ["c_"+finger_type+"1_ik"+side, "c_"+finger_type+"2_ik"+side, "c_"+finger_type+"3_ik"+side]

    if root_finger['ik_tip'] == 0:# only the first two phalanges must be snapped if ik2, since the last is the IK target
        fk_fingers.pop()
        ik_fingers.pop()

    phal1 = get_pose_bone(fk_fingers[0])
    phal2 = get_pose_bone(fk_fingers[1])    
    
    
    #   constraint support
    pole_cns, bpar_name, par_type, valid_cns = get_active_child_of_cns(ik_pole)
    
    if pole_cns and valid_cns:
        bone_parent = get_pose_bone(bpar_name)
        ik_pole.matrix = bone_parent.matrix_channel.inverted() @ Matrix.Translation((phal2.z_axis.normalized() * phal2.length * 1.3 * fingers_ik_pole_distance)) @ phal2.matrix
    else:
        ik_pole.matrix = Matrix.Translation((phal2.z_axis.normalized() * phal2.length * 1.3 * fingers_ik_pole_distance)) @ phal2.matrix

    update_transform()
    compensate_ik_pole_position(phal1, phal2, get_pose_bone(ik_fingers[0]), get_pose_bone(ik_fingers[1]), ik_pole)
    
    ik_pole.rotation_euler = [0,0,0]
    '''
    # Old method, snap individual phalanges rotation.
    # Breaks in current version, then disable
    # Also compensate_ik_pole_position() is performing better, so no use for now
    #   phalanges
    for iter in range(0,4):
        for i, bname in enumerate(ik_fingers):
            b_ik = get_pose_bone(bname)
            loc, scale = b_ik.location.copy(), b_ik.scale.copy()
            b_fk = get_pose_bone(fk_fingers[i])
            b_ik.matrix = b_fk.matrix.copy()
            # restore loc and scale, only rotation for better results
            b_ik.location = loc
            b_ik.scale = scale
            # update hack
            update_transform()
    '''
    # Switch prop
    root_finger['ik_fk_switch'] = 0.0

    # udpate hack
    update_transform()

    #insert key if autokey enable
    if bpy.context.scene.tool_settings.use_keyframe_insert_auto:
        root_finger.keyframe_insert(data_path='["ik_fk_switch"]')

        for bname in ik_fingers + fk_fingers + [ik_target.name]:
            pb = get_pose_bone(bname)
            pb.keyframe_insert(data_path="location")
            if pb.rotation_mode != "QUATERNION":
                pb.keyframe_insert(data_path="rotation_euler")
            else:
                pb.keyframe_insert(data_path="rotation_quaternion")
            
            for i, j in enumerate(pb.lock_scale):
                if not j:
                    pb.keyframe_insert(data_path="scale", index=i)
          

def fk_to_ik_finger(root_finger, side):
    finger_type = None

    for i in fingers_type_list:
        if i in root_finger.name:
            finger_type = i
            break
    '''
    ik_target_name = "c_"+finger_type+"_ik"+side
    ik_target = get_pose_bone(ik_target_name)
    if ik_target == None:
        print("Finger IK target not found:", ik_target_name)
        return
    '''
    
    # snap
    fk_fingers = ["c_"+finger_type+"1"+side, "c_"+finger_type+"2"+side, "c_"+finger_type+"3"+side]
    fk_fingers = []
    ik_fingers = []
    
    if get_pose_bone('c_'+finger_type+str(i)+'_ik3'+side) == None:#backward-compatibility
        root_finger['ik_tip'] = 0
    
    for i in range(1, 4):
        fk_fingers.append('c_'+finger_type+str(i)+side)
        if root_finger['ik_tip'] == 0:
            ik_fingers.append('c_'+finger_type+str(i)+'_ik'+side)
        else:
            ik_fingers.append('c_'+finger_type+str(i)+'_ik3'+side)            

            
    for i in range(0,2):
        for i, name in enumerate(fk_fingers):
            b_fk = get_pose_bone(name)
            b_ik = get_pose_bone(ik_fingers[i])
            b_fk.matrix = b_ik.matrix.copy()

            # udpate hack
            update_transform()

     #switch
    root_finger['ik_fk_switch'] = 1.0

    # udpate hack
    update_transform()

    #insert key if autokey enable
    if bpy.context.scene.tool_settings.use_keyframe_insert_auto:
        root_finger.keyframe_insert(data_path='["ik_fk_switch"]')

        for bname in ik_fingers + fk_fingers:# + [ik_target.name]:
            pb = get_pose_bone(bname)
            pb.keyframe_insert(data_path="location")
            if pb.rotation_mode != "QUATERNION":
                pb.keyframe_insert(data_path="rotation_euler")
            else:
                pb.keyframe_insert(data_path="rotation_quaternion")
            
            for i, j in enumerate(pb.lock_scale):
                if not j:
                    pb.keyframe_insert(data_path="scale", index=i) 
                    
                    
def tip_to_root_finger(root_finger, side):
    print('Snap tip to root...')
    scn = bpy.context.scene
    
    finger_type = None
    rig = bpy.context.active_object

    for i in fingers_type_list:
        if i in root_finger.name:
            finger_type = i
            break

    ik_target_name = ''
    ik_target_name = 'c_'+finger_type+'_ik'+side
    ik_target2_name = 'c_'+finger_type+'_ik2'+side
    ik_target = get_pose_bone(ik_target_name)
    ik_target2 = get_pose_bone(ik_target2_name)

    if ik_target == None or ik_target2 == None:
        print('Finger IK target not found')
        return

    ik_pole_name = 'c_'+finger_type+'_pole'+side
    ik_pole = get_pose_bone(ik_pole_name)
    if ik_pole == None:
        print('Finger IK pole not found:', ik_pole_name)
        return
     
    if root_finger['ik_tip'] == 1:# already in tip mode, skip
        return

    # Snap IK target
        # constraint support
    constraint, bparent_name, parent_type, valid_constraint = get_active_child_of_cns(ik_target)
    finger3_ik = get_pose_bone('c_'+finger_type+'3_ik'+side)

    if constraint and valid_constraint:
        if parent_type == 'bone':
            bone_parent = get_pose_bone(bparent_name)
            ik_target.matrix = bone_parent.matrix_channel.inverted() @ finger3_ik.matrix
            update_transform()
            # set head to tail position
            tail_mat = bone_parent.matrix_channel.inverted() @ Matrix.Translation((ik_target.y_axis.normalized() * ik_target.length))
            ik_target.matrix = tail_mat @ ik_target.matrix

        if parent_type == 'object':
            obj = bpy.data.objects.get(bparent_name)
            ik_target.matrix = constraint.inverse_matrix.inverted() @ obj.matrix_world.inverted() @ finger3_ik.matrix
            update_transform()
            # set head to tail position
            tail_mat = constraint.inverse_matrix.inverted() @ obj.matrix_world.inverted() @ Matrix.Translation((ik_target.y_axis.normalized() * ik_target.length))
            ik_target.matrix = tail_mat @ ik_target.matrix
    else:
        ik_target.matrix = finger3_ik.matrix
        update_transform()
        # set head to tail position
        tail_mat = Matrix.Translation((ik_target.y_axis.normalized() * ik_target.length))
        ik_target.matrix = tail_mat @ ik_target.matrix

    update_transform()

    # Snap phalanges
    ik_fingers = []
    ik3_fingers = []
    
    for i in range(2, 4):
        ik_fingers.append('c_'+finger_type+str(i)+'_ik'+side)
        ik3_fingers.append('c_'+finger_type+str(i)+'_ik3'+side)

    #   store mats
    fingers_mat = []
    for bname in ik_fingers:
        b_ik = get_pose_bone(bname)
        fingers_mat.append(b_ik.matrix.copy())

    # Switch prop
    root_finger['ik_tip'] = 1
    
    for iter in range(0, 4):# progressive refine through iterations
        for i, bname in enumerate(ik3_fingers):
            b_ik = get_pose_bone(bname)
            loc, scale = b_ik.location.copy(), b_ik.scale.copy()
            b_ik.matrix = fingers_mat[i]
            # restore loc and scale, only rotation for better results
            b_ik.location = loc
            b_ik.scale = scale
        # update hack
        update_transform()
        

    #insert key if autokey enable
    if scn.tool_settings.use_keyframe_insert_auto:
        root_finger.keyframe_insert(data_path='["ik_tip"]')

        for bname in ik3_fingers+[ik_target.name, ik_target2.name]:
            pb = get_pose_bone(bname)
            pb.keyframe_insert(data_path="location")
            if pb.rotation_mode != "QUATERNION":
                pb.keyframe_insert(data_path="rotation_euler")
            else:
                pb.keyframe_insert(data_path="rotation_quaternion")
                
            for i, j in enumerate(pb.lock_scale):
                if not j:
                    pb.keyframe_insert(data_path="scale", index=i)
                    

def root_to_tip_finger(root_finger, side):
    print('Snap root to tip...')
    scn = bpy.context.scene
    finger_type = None
    rig = bpy.context.active_object

    for i in fingers_type_list:
        if i in root_finger.name:
            finger_type = i
            break

    pole_name = 'c_'+finger_type+'_pole'+side
    pole_pb = get_pose_bone(pole_name)
    ik_target_tip_name = 'c_'+finger_type+'_ik'+side
    ik_target_root_name = 'c_'+finger_type+'_ik2'+side
    ik_target_tip = get_pose_bone(ik_target_tip_name)
    ik_target_root = get_pose_bone(ik_target_root_name)

    if ik_target_tip == None or ik_target_root == None:
        print('Finger IK target not found')
        return

    ik_pole_name = 'c_'+finger_type+'_pole'+side
    ik_pole = get_pose_bone(ik_pole_name)
    if ik_pole == None:
        print('Finger IK pole not found:', ik_pole_name)
        return
        
    if root_finger['ik_tip'] == 0:# already in root mode, skip
        return

    # Snap IK target
    finger3_ik = get_pose_bone('c_'+finger_type+'3_ik3'+side)
    snap_bone_matrix(ik_target_root, finger3_ik.matrix) 

    update_transform()
    
    ik_fingers = ['c_'+finger_type+'1_ik'+side, 'c_'+finger_type+'2_ik'+side]
    
    # store current matrices
    fingers_mat = []
    for i, bname in enumerate(ik_fingers):
        b_ik = get_pose_bone(bname)
        fingers_mat.append(b_ik.matrix.copy())
        
    pole_mat = pole_pb.matrix.copy()

    # Switch prop
    root_finger['ik_tip'] = 0
    
    update_transform()
    
    # Snap
    #   pole
    snap_bone_matrix(pole_pb, pole_mat)
    
    #   phalanges
    for iter in range(0,4):
        for i, bname in enumerate(ik_fingers):
            b_ik = get_pose_bone(bname)
            loc, scale = b_ik.location.copy(), b_ik.scale.copy()
            b_ik.matrix = fingers_mat[i]
            # restore loc and scale, only rotation for better results
            b_ik.location = loc
            b_ik.scale = scale
        # update hack
        update_transform()


    #insert key if autokey enable
    if scn.tool_settings.use_keyframe_insert_auto:
        root_finger.keyframe_insert(data_path='["ik_tip"]')

        for bname in ik_fingers+[ik_target_tip.name, ik_target_root.name]:
            pb = get_pose_bone(bname)
            pb.keyframe_insert(data_path='location')
            if pb.rotation_mode != 'QUATERNION':
                pb.keyframe_insert(data_path='rotation_euler')
            else:
                pb.keyframe_insert(data_path='rotation_quaternion')
            
            for i, j in enumerate(pb.lock_scale):
                if not j:
                    pb.keyframe_insert(data_path='scale', index=i)
       

#   IK FK arms
def bake_fk_to_ik_arm(self):
    armature = bpy.context.active_object
    
    if self.one_key_per_frame:# bake all frames
        for f in range(self.frame_start, self.frame_end +1):
            bpy.context.scene.frame_set(f)
            for _s in self.selected_sides:
                fk_to_ik_arm(bpy.context.active_object, _s, add_keyframe=True)
    
    else:
        # bake only existing keyframes
        # collect frames that have keyframes
        arms_ik_ctrl = [ard.arm_bones_dict['shoulder']['control'], ard.arm_bones_dict['arm']['control_ik'],
                        ard.arm_bones_dict['hand']['control_ik'], ard.arm_bones_dict['control_pole_ik']]
                        
        frames_idx_dict = {}# for each side
        
        for _s in self.selected_sides:
            frames_idx = []
            for base_name in arms_ik_ctrl:
                bname = base_name+_s
                fc_start_dp = 'pose.bones["'+bname+'"].'
                
                for fc in get_action_fcurves(armature.animation_data.action):
                    if fc.data_path.startswith(fc_start_dp):
                        for keyf in fc.keyframe_points:
                            if keyf.co[0] >= self.frame_start and keyf.co[0] <= self.frame_end:
                                if not keyf.co[0] in frames_idx:
                                    frames_idx.append(keyf.co[0])
            
            frames_idx_dict[_s] = frames_idx
        
        for f in range(self.frame_start, self.frame_end +1):
            found_frame = []
            for _s in self.selected_sides:
                if f in frames_idx_dict[_s]:
                    found_frame.append(_s)
                    
            if len(found_frame):
                bpy.context.scene.frame_set(int(f))    
                for _s in found_frame:
                    fk_to_ik_arm(armature, _s, add_keyframe=True)


def fk_to_ik_arm(obj, side, add_keyframe=False):

    arm_fk = get_pose_bone(fk_arm[0]+side)
    forearm_fk = get_pose_bone(fk_arm[1]+side)
    hand_fk = get_pose_bone(fk_arm[2]+side)

    arm_ik = get_pose_bone(ik_arm[0]+side)
    forearm_ik = get_pose_bone(ik_arm[1]+side)
    hand_ik = get_pose_bone(ik_arm[2]+side)
    ik_offset = get_pose_bone(ik_arm[5]+side)
    ik_pivot = get_pose_bone(ik_arm[6]+side)
    pole = get_pose_bone(ik_arm[3]+side)
    hand_def = get_pose_bone('hand'+side)
    
    # Stretch
    if hand_ik['auto_stretch'] == 0.0:
        hand_fk['stretch_length'] = hand_ik['stretch_length']
    else:
        diff = (arm_ik.length+forearm_ik.length) / (arm_fk.length+forearm_fk.length)
        hand_fk['stretch_length'] *= diff

    #Snap rot
    snap_rot(arm_fk, arm_ik)
    snap_rot(forearm_fk, forearm_ik)
    
    hand_rot_ik_tar = get_pose_bone(hand_def.constraints.get('rotIK').subtarget)
    snap_rot(hand_fk, hand_rot_ik_tar)

    #Snap scale
    hand_fk.scale =hand_ik.scale

    #rot debug
    forearm_fk.rotation_euler[0] = 0
    forearm_fk.rotation_euler[1] = 0

    #switch
    hand_ik['ik_fk_switch'] = 1.0

    #udpate view   
    bpy.context.view_layer.update()

    #insert key if autokey enable
    if bpy.context.scene.tool_settings.use_keyframe_insert_auto or add_keyframe:
        # switch
        hand_ik.keyframe_insert(data_path='["ik_fk_switch"]')
        #fk chain
        hand_fk.keyframe_insert(data_path='["stretch_length"]')
        keyframe_pb_transforms(hand_fk, loc=False)
        keyframe_pb_transforms(arm_fk, loc=False, scale=False)
        keyframe_pb_transforms(forearm_fk, loc=False, scale=False, keyf_locked=True)

        #ik chain
        hand_ik.keyframe_insert(data_path='["stretch_length"]')
        hand_ik.keyframe_insert(data_path='["auto_stretch"]')
        keyframe_pb_transforms(hand_ik)
        pole.keyframe_insert(data_path='location')

    # change hand IK to FK selection, if selected    
    if is_pbone_selected(hand_ik):
        select_pbone(hand_fk)
        obj.data.bones.active = hand_fk.bone
        select_pbone(hand_ik, state=False)
        

def bake_ik_to_fk_arm(self):
    armature = bpy.context.active_object
    
    if self.one_key_per_frame:# bake all frames        
        for f in range(self.frame_start, self.frame_end +1):
            bpy.context.scene.frame_set(f)
            for _s in self.selected_sides:
                ik_to_fk_arm(armature, _s, add_keyframe=True)
            
    else:# bake only existing keyframes
        # collect frames that have keyframes
        arms_fk_ctrl = [ard.arm_bones_dict['shoulder']['control'], ard.arm_bones_dict['arm']['control_fk'],
                        ard.arm_bones_dict['forearm']['control_fk'], ard.arm_bones_dict['hand']['control_fk']]
                        
        frames_idx_dict = {}# for each side
        
        for _s in self.selected_sides:
            frames_idx = []
            for base_name in arms_fk_ctrl:
                bname = base_name+_s
                fc_start_dp = 'pose.bones["'+bname+'"].'

                for fc in get_action_fcurves(armature.animation_data.action):
                    if fc.data_path.startswith(fc_start_dp):
                        for keyf in fc.keyframe_points:
                            if keyf.co[0] >= self.frame_start and keyf.co[0] <= self.frame_end:
                                if not keyf.co[0] in frames_idx:
                                    frames_idx.append(keyf.co[0])
                                    
            frames_idx_dict[_s] = frames_idx
            
        for f in range(self.frame_start, self.frame_end +1):
            found_frame = []
            for _s in self.selected_sides:
                if f in frames_idx_dict[_s]:
                    found_frame.append(_s)
                    
            if len(found_frame):
                bpy.context.scene.frame_set(int(f))    
                for _s in found_frame:
                    ik_to_fk_arm(armature, _s, add_keyframe=True)
                

def ik_to_fk_arm(obj, side, add_keyframe=False):
    
    arm_fk = get_pose_bone(fk_arm[0]+side)
    forearm_fk = get_pose_bone(fk_arm[1]+side)
    hand_fk = get_pose_bone(fk_arm[2]+side)   

    arm_ik = get_pose_bone(ik_arm[0]+side)
    forearm_ik = get_pose_bone(ik_arm[1]+side)
    hand_ik = get_pose_bone(ik_arm[2]+side)
    ik_offset = get_pose_bone(ik_arm[5]+side)
    ik_pivot = get_pose_bone(ik_arm[6]+side)
    pole = get_pose_bone(ik_arm[3]+side)
    
    # reset custom pole angle if any
    if get_pose_bone("c_arm_ik"+side):
        get_pose_bone("c_arm_ik"+side).rotation_euler[1] = 0.0
    
    # Stretch
    hand_ik['stretch_length'] = hand_fk['stretch_length']
    
    # Snap
    if ik_pivot:
        zero_out_pb(ik_pivot)
    if ik_offset:
        zero_out_pb(ik_offset)
    
    #   constraint support
    constraint = None
    bparent_name = ''
    parent_type = ''
    valid_constraint = True

    if len(hand_ik.constraints) > 0:
        for c in hand_ik.constraints:
            if not c.mute and c.influence > 0.5 and c.type == 'CHILD_OF':
                if c.target:
                    #if bone
                    if c.target.type == 'ARMATURE':
                        bparent_name = c.subtarget
                        parent_type = "bone"
                        constraint = c
                    #if object
                    else:
                        bparent_name = c.target.name
                        parent_type = "object"
                        constraint = c


    if constraint != None:
        if parent_type == "bone":
            if bparent_name == "":
                valid_constraint = False

    if constraint and valid_constraint:
        if parent_type == "bone":
            bone_parent = bpy.context.object.pose.bones[bparent_name]
            hand_ik.matrix = bone_parent.matrix_channel.inverted()@ hand_fk.matrix
        if parent_type == "object":
            bone_parent = bpy.data.objects[bparent_name]
            obj_par = bpy.data.objects[bparent_name]
            hand_ik.matrix = constraint.inverse_matrix.inverted() @ obj_par.matrix_world.inverted() @ hand_fk.matrix
    else:
        hand_ik.matrix = hand_fk.matrix

    # Pole target position
    pole_dist = 1.0
    hand_ref = get_data_bone("hand_ref"+side)
    if hand_ref:
        if "ik_pole_distance" in hand_ref.keys():
            pole_dist = hand_ref["ik_pole_distance"]
    
    pole_rot = pole.rotation_euler.copy()# preserve the rotation, should not change
    
    pole_pos = get_ik_pole_pos(arm_fk, forearm_fk, pole_dist)
    pole_mat = Matrix.Translation(pole_pos)
    snap_bone_matrix(pole, pole_mat)
    
    # there may be still an offset angle in case automatic IK roll alignment if disabled
    # compensate
    compensate_ik_pole_position(arm_fk, forearm_fk, arm_ik, forearm_ik, pole)
    
    pole.rotation_euler = pole_rot
    
    # switch
    hand_ik['ik_fk_switch'] = 0.0

    #update view  
    bpy.context.view_layer.update()  

     #insert key if autokey enable
    if bpy.context.scene.tool_settings.use_keyframe_insert_auto or add_keyframe:
        #ik chain
        hand_ik.keyframe_insert(data_path='["ik_fk_switch"]')
        hand_ik.keyframe_insert(data_path='["stretch_length"]')
        hand_ik.keyframe_insert(data_path='["auto_stretch"]')
        keyframe_pb_transforms(hand_ik)
        if ik_offset:
            keyframe_pb_transforms(ik_offset)
        if ik_pivot:
            keyframe_pb_transforms(ik_pivot)
        pole.keyframe_insert(data_path="location")

        # ik rot controller if any
        if obj.pose.bones.get('c_arm_ik' + side) != None:
            get_pose_bone('c_arm_ik' + side).keyframe_insert(data_path="rotation_euler", index=1)    

        #fk chain
        hand_fk.keyframe_insert(data_path='["stretch_length"]')
        keyframe_pb_transforms(hand_fk) 
        keyframe_pb_transforms(arm_fk, loc=False, scale=False)       
        keyframe_pb_transforms(forearm_fk, loc=False, scale=False)

    # change FK to IK hand selection, if selected
    if is_pbone_selected(hand_fk):
        select_pbone(hand_ik)
        obj.data.bones.active = hand_ik.bone
        select_pbone(hand_fk, state=False)
        
    #update hack
    update_transform()


#   IK FK legs
def bake_fk_to_ik_leg(self):
    armature = bpy.context.active_object
    c_thigh_b_dict = {}
    c_leg_ik3_dict = {}
    foot_iks_dict = {}
    
    for _s in self.selected_sides:
        c_thigh_b_dict[_s] = get_pose_bone(ik_leg[11]+_s)
        c_leg_ik3_dict[_s] = get_pose_bone(ik_leg[12]+_s)
        foot_iks_dict[_s] = get_pose_bone(ik_leg[2]+_s)
    
    print("self.selected_sides", self.selected_sides)
    c_thigh_b_rots_dict = {}
    
    
    def save_c_thigh_b_rots(frames, _s):
        # if 3 bones leg type 1, we need to save rot of c_thigh_b on each frame
        # since the same ctrl is used both for IK and FK chain
        # and restore on each frame
        c_thigh_b_rots = {}
        c_thigh_b = c_thigh_b_dict[_s]
        
        for f in frames:
            bpy.context.scene.frame_set(int(f))
            c_thigh_b_rots[int(f)] = (c_thigh_b.rotation_euler.copy() if c_thigh_b.rotation_mode != 'QUATERNION' else c_thigh_b.rotation_quaternion.copy())
        
        c_thigh_b_rots_dict[_s] = c_thigh_b_rots
        

    def restore_c_thigh_b_rots(fi, _s):
        c_thigh_b = c_thigh_b_dict[_s]
        foot_ik = foot_iks_dict[_s]
        foot_ik['ik_fk_switch'] = 0.0# need to switch back to IK first        
        
        if c_thigh_b.rotation_mode == 'QUATERNION':
            c_thigh_b.rotation_quaternion = c_thigh_b_rots_dict[_s][fi]
        else:
            c_thigh_b.rotation_euler = c_thigh_b_rots_dict[_s][fi]
        
        update_transform()
        
        
    if self.one_key_per_frame:# bake all frames
        for _s in self.selected_sides:
            c_leg_ik3 = c_leg_ik3_dict[_s]
            c_thigh_b = c_thigh_b_dict[_s]
            
            # special, 3 bones leg type 1. Since c_thigh_b is in both IK-FK chains, must be saved and backed up when snapping
            if c_leg_ik3 == None and c_thigh_b and "three_bones_ik" in foot_iks_dict[_s].keys():     
                save_c_thigh_b_rots([f for f in range(self.frame_start, self.frame_end +1)], _s)
        
        # bake on each frame
        for f in range(self.frame_start, self.frame_end +1):
            bpy.context.scene.frame_set(f)
            
            for _s in self.selected_sides:
                # 3 bones leg type 1, restore c_thigh_b first
                if _s in c_thigh_b_rots_dict:
                    restore_c_thigh_b_rots(f, _s)
                # snap
                fk_to_ik_leg(armature, _s, add_keyframe=True)
              
        
    else:# bake only existing keyframes
        # collect frames that have keyframes
        legs_ik_ctrl = [ard.leg_bones_dict['upthigh'], ard.leg_bones_dict['thigh']['control_ik'],
                        ard.leg_bones_dict['foot']['control_ik'], ard.leg_bones_dict['foot']['control_reverse'],
                        ard.leg_bones_dict['foot']['control_roll'], ard.leg_bones_dict['foot']['control_ik_offset'],
                        ard.leg_bones_dict['toes']['control_ik'], ard.leg_bones_dict['toes']['control_pivot'],
                        ard.leg_bones_dict['control_pole_ik'], ard.leg_bones_dict['calf']['control_ik3']]
        
        
        frames_idx_dict = {}
        frames_idx_all = []
        
        for _s in self.selected_sides:
        
            frames_idx = []
            
            # iterate through controllers and collect keyframed frames
            for base_name in legs_ik_ctrl:
                bname = base_name+_s
                fc_start_dp = 'pose.bones["'+bname+'"].'

                for fc in get_action_fcurves(armature.animation_data.action):
                    if fc.data_path.startswith(fc_start_dp):
                        for keyf in fc.keyframe_points:
                            if keyf.co[0] >= self.frame_start and keyf.co[0] <= self.frame_end:
                                if not keyf.co[0] in frames_idx:
                                    frames_idx.append(keyf.co[0])
                                if not keyf.co[0] in frames_idx_all:
                                    frames_idx_all.append(keyf.co[0])
                                    
            frames_idx_dict[_s] = frames_idx
            
            # special, 3 bones leg type 1. Since c_thigh_b is in both IK-FK chains, must be saved and backed up when snapping
            for f in frames_idx_all:     
                for _s in self.selected_sides:
                    c_leg_ik3 = c_leg_ik3_dict[_s]
                    c_thigh_b = c_thigh_b_dict[_s]
                    if c_leg_ik3 == None and c_thigh_b and "three_bones_ik" in foot_iks_dict[_s].keys():# 3 bones leg type 1               
                        save_c_thigh_b_rots(frames_idx_all, _s)
                        
        # bake on each keyframed frame                
        for f in range(self.frame_start, self.frame_end +1):
            found_frame = []
            for _s in self.selected_sides:
                if f in frames_idx_dict[_s]:
                    found_frame.append(_s)
                    
            if len(found_frame):
                bpy.context.scene.frame_set(int(f))
                
                for _s in found_frame:   
                    # 2 bones leg type 1, backup c_thigh_b rot first
                    if _s in c_thigh_b_rots_dict:
                        restore_c_thigh_b_rots(f, _s)
                    # snap
                    fk_to_ik_leg(armature, _s, add_keyframe=True)


def fk_to_ik_leg(obj, side, add_keyframe=False):
    thigh_fk  = get_pose_bone(fk_leg[0] + side)
    leg_fk  = get_pose_bone(fk_leg[1] + side)
    foot_fk  = get_pose_bone(fk_leg[2] + side)
    toes_fk = get_pose_bone(fk_leg[3] + side)
    thigh_b_fk = get_pose_bone(fk_leg[5]+side)
    
    thigh_ik = get_pose_bone(ik_leg[0] + side)
    thigh_ik_nostr = get_pose_bone(ik_leg[0]+'_nostr'+side)
    leg_ik = get_pose_bone(ik_leg[1] + side)
    leg_ik_nostr = get_pose_bone(ik_leg[1]+'_nostr'+side)
    foot_ik = get_pose_bone(ik_leg[2] + side)
    pole = get_pose_bone(ik_leg[3] + side)
    toes_ik = get_pose_bone(ik_leg[4] + side)
    foot_01 = get_pose_bone(ik_leg[5] + side)
    foot_roll = get_pose_bone(ik_leg[6] + side)
    footi_rot = get_pose_bone(ik_leg[7] + side)
    c_leg_ik3 = get_pose_bone(ik_leg[12]+side)
    thigh_b_ik3_rev = get_pose_bone("thigh_b_ik3_rev"+side)
    thigh_ik3_rev = get_pose_bone('thigh_ik3_rev'+side)
    leg_ik3_snap = get_pose_bone('leg_ik3_snap'+side)
    thigh = get_pose_bone('thigh'+side)
    c_thigh_b = get_pose_bone(ik_leg[11]+side)
    leg = get_pose_bone('leg'+side)
    
    if c_leg_ik3:# 3 Bones Leg Type 2
    
        # Stretch
        soft_ik = 'leg_softik' in foot_ik.keys()
        
        if foot_ik['auto_stretch'] == 0.0 and soft_ik == False:
            foot_fk['stretch_length'] = foot_ik['stretch_length']       
        else:
            diff = (thigh_b_ik3_rev.length+thigh_ik3_rev.length+leg_ik3_snap.length) / (thigh_b_fk.length+thigh_fk.length+leg_fk.length)
            foot_fk['stretch_length'] *= diff
            
        # c_thigh_b_fk snap
        snap_rot(thigh_b_fk, thigh_b_ik3_rev)
        
        # thigh_fk snap
        snap_rot(thigh_fk, thigh_ik3_rev)
        
        # rotation debug
        thigh_fk.rotation_euler[0] = 0.0
        thigh_fk.rotation_euler[1] = 0.0
        
        # leg_fk snap
        snap_rot(leg_fk, leg_ik3_snap)
        
        # foot_fk snap
        snap_rot(foot_fk, footi_rot)
        #   scale
        foot_fk.scale =foot_ik.scale
        
        #Toes snap
        snap_rot(toes_fk, toes_ik)
        #   scale
        toes_fk.scale =toes_ik.scale
        
        # rotation debug
        #leg_fk.rotation_euler[0] = 0.0
        #leg_fk.rotation_euler[1] = 0.0
        
        #print('FRAME CURRENT', bpy.context.scene.frame_current)
        #if bpy.context.scene.frame_current == 20:
        #    print(br)
            
        # switch
        foot_ik['ik_fk_switch'] = 1.0
                
        # udpate hack  
        bpy.context.view_layer.update()
        
        #insert key if autokey enable
        if bpy.context.scene.tool_settings.use_keyframe_insert_auto or add_keyframe:
            # switch
            foot_ik.keyframe_insert(data_path='["ik_fk_switch"]')
            #fk chain            
            foot_fk.keyframe_insert(data_path='["stretch_length"]')
            keyframe_pb_transforms(thigh_b_fk, loc=False, scale=False)
            keyframe_pb_transforms(thigh_fk, loc=False, scale=False)
            keyframe_pb_transforms(leg_fk, loc=False, scale=False, keyf_locked=True)
            keyframe_pb_transforms(foot_fk, loc=False)
            keyframe_pb_transforms(toes_fk, loc=False)
            
            #ik chain            
            foot_ik.keyframe_insert(data_path='["stretch_length"]')
            foot_ik.keyframe_insert(data_path='["auto_stretch"]')
            keyframe_pb_transforms(foot_ik) 
            keyframe_pb_transforms(c_leg_ik3, loc=False, scale=False)
            keyframe_pb_transforms(foot_01, loc=False, scale=False)
            keyframe_pb_transforms(foot_roll, rot=False, scale=False)
            keyframe_pb_transforms(toes_ik, loc=False)
            keyframe_pb_transforms(pole, rot=False, scale=False)
        
        
    else:# 2 Bones Leg and 3 Bones Leg Type 1
    
        # save the c_thigh_b matrix if any        
        if c_thigh_b:
            c_thigh_b_matrix = c_thigh_b.matrix.copy()

        # Stretch
        soft_ik = 'leg_softik' in foot_ik.keys()
        
        if foot_ik['auto_stretch'] == 0.0 and soft_ik == False:
            foot_fk['stretch_length'] = foot_ik['stretch_length']       
        else:
            diff = (thigh_ik.length+leg_ik.length) / (thigh_fk.length+leg_fk.length)
            foot_fk['stretch_length'] *= diff

        # Thigh snap
        snap_rot(thigh_fk, thigh_ik)

        # Leg snap
        snap_rot(leg_fk, leg_ik)

        # foot_fk snap
        snap_rot(foot_fk, footi_rot)
        #   scale
        foot_fk.scale =foot_ik.scale

        #Toes snap
        snap_rot(toes_fk, toes_ik)
        #   scale
        toes_fk.scale =toes_ik.scale

        # rotation debug
        leg_fk.rotation_euler[0] = 0.0
        leg_fk.rotation_euler[1] = 0.0

        # switch
        foot_ik['ik_fk_switch'] = 1.0

        # udpate hack  
        bpy.context.view_layer.update()

        if c_thigh_b:
            c_thigh_b.matrix = c_thigh_b_matrix.copy()


        #insert key if autokey enable
        if bpy.context.scene.tool_settings.use_keyframe_insert_auto or add_keyframe:        
            # switch
            foot_ik.keyframe_insert(data_path='["ik_fk_switch"]')
            # fk chain
            foot_fk.keyframe_insert(data_path='["stretch_length"]')
            
            keyframe_pb_transforms(foot_fk, loc=False)
            keyframe_pb_transforms(thigh_fk, loc=False, scale=False)
            keyframe_pb_transforms(leg_fk, loc=False, scale=False, keyf_locked=True)
            keyframe_pb_transforms(toes_fk, loc=False)
          
            #ik chain
            foot_ik.keyframe_insert(data_path='["stretch_length"]')
            foot_ik.keyframe_insert(data_path='["auto_stretch"]')
            keyframe_pb_transforms(foot_ik)   

            if c_thigh_b:
                keyframe_pb_transforms(c_thigh_b)
            foot_01.keyframe_insert(data_path='rotation_euler')
            foot_roll.keyframe_insert(data_path='location')
            keyframe_pb_transforms(toes_ik, loc=False)
            pole.keyframe_insert(data_path="location")

            #ik angle controller if any
            if get_pose_bone('c_thigh_ik'+side) != None:
                get_pose_bone('c_thigh_ik'+side).keyframe_insert(data_path='rotation_euler', index=1)

    # change IK to FK foot selection, if selected
    if is_pbone_selected(foot_ik) and not add_keyframe:
        select_pbone(foot_fk)
        obj.data.bones.active = foot_fk.bone   
        select_pbone(foot_ik, state=False)


def bake_ik_to_fk_leg(self):
    armature = bpy.context.active_object   
    c_thigh_b_dict = {}
    c_leg_ik3_dict = {}
    foot_iks_dict = {}
    
    for _s in self.selected_sides:
        c_thigh_b_dict[_s] = get_pose_bone(ik_leg[11]+_s)
        c_leg_ik3_dict[_s] = get_pose_bone(ik_leg[12]+_s)
        foot_iks_dict[_s] = get_pose_bone(ik_leg[2]+_s)
    
    print("self.selected_sides", self.selected_sides)
    c_thigh_b_rots_dict = {}
    
    def save_c_thigh_b_rots(frames, _s):
        # if 3 bones leg type 1, we need to save rot of c_thigh_b on each frame
        # since the same ctrl is used both for IK and FK chain
        # and restore on each frame
        c_thigh_b_rots = {}
        c_thigh_b = c_thigh_b_dict[_s]
        
        for f in frames:
            bpy.context.scene.frame_set(int(f))
            c_thigh_b_rots[int(f)] = (c_thigh_b.rotation_euler.copy() if c_thigh_b.rotation_mode != 'QUATERNION' else c_thigh_b.rotation_quaternion.copy())
        
        c_thigh_b_rots_dict[_s] = c_thigh_b_rots
    

    def restore_c_thigh_b_rots(fi, _s):
        c_thigh_b = c_thigh_b_dict[_s]
        foot_ik = foot_iks_dict[_s]
        foot_ik['ik_fk_switch'] = 0.0# need to switch back to IK first        
        
        if c_thigh_b.rotation_mode == 'QUATERNION':
            c_thigh_b.rotation_quaternion = c_thigh_b_rots_dict[_s][fi]
        else:
            c_thigh_b.rotation_euler = c_thigh_b_rots_dict[_s][fi]
        
        update_transform()
            
                    
    if self.one_key_per_frame:# bake all frames
        for _s in self.selected_sides:
            c_leg_ik3 = c_leg_ik3_dict[_s]
            c_thigh_b = c_thigh_b_dict[_s]
            
            # special, 3 bones leg type 1. Since c_thigh_b is in both IK-FK chains, must be saved and backed up when snapping
            if c_leg_ik3 == None and c_thigh_b and "three_bones_ik" in foot_iks_dict[_s].keys():     
                save_c_thigh_b_rots([f for f in range(self.frame_start, self.frame_end +1)], _s)
     
            
        # bake on each frame
        for fi, f in enumerate(range(self.frame_start, self.frame_end + 1)):
            bpy.context.scene.frame_set(f)
            
            for _s in self.selected_sides:
                # 3 bones leg type 1, restore c_thigh_b first
                if _s in c_thigh_b_rots_dict:
                    restore_c_thigh_b_rots(fi, _s)
                # snap
                ik_to_fk_leg(armature, _s, add_keyframe=True)            
       
    
    else:# bake only existing keyframes
        # collect frames that have keyframes
        legs_fk_ctrl = [
            ard.leg_bones_dict['upthigh'], ard.leg_bones_dict['thigh']['control_fk'], 
            ard.leg_bones_dict['calf']['control_fk'],
            ard.leg_bones_dict['foot']['control_fk'], ard.leg_bones_dict['toes']['control_fk']]
        
        frames_idx_dict = {}
        frames_idx_all = []
        
        for _s in self.selected_sides:
        
            frames_idx = []
            
            # iterate through controllers and collect keyframed frames
            for base_name in legs_fk_ctrl:
                bname = base_name+_s
                fc_start_dp = 'pose.bones["'+bname+'"].'

                for fc in get_action_fcurves(armature.animation_data.action):
                    if fc.data_path.startswith(fc_start_dp):
                        for keyf in fc.keyframe_points:
                            if keyf.co[0] >= self.frame_start and keyf.co[0] <= self.frame_end:
                                if not keyf.co[0] in frames_idx:
                                    frames_idx.append(keyf.co[0])
                                if not keyf.co[0] in frames_idx_all:
                                    frames_idx_all.append(keyf.co[0])
                                    
            frames_idx_dict[_s] = frames_idx
            
            # special, 3 bones leg type 1. Since c_thigh_b is in both IK-FK chains, must be saved and backed up when snapping
            for f in frames_idx_all:     
                for _s in self.selected_sides:
                    c_leg_ik3 = c_leg_ik3_dict[_s]
                    c_thigh_b = c_thigh_b_dict[_s]
                    if c_leg_ik3 == None and c_thigh_b and "three_bones_ik" in foot_iks_dict[_s].keys():# 3 bones leg type 1               
                        save_c_thigh_b_rots(frames_idx_all, _s)
        
     
        # bake on each keyframed frame                
        for f in range(self.frame_start, self.frame_end +1):
            found_frame = []
            for _s in self.selected_sides:
                if f in frames_idx_dict[_s]:
                    found_frame.append(_s)
                    
            if len(found_frame):
                bpy.context.scene.frame_set(int(f))
                
                for _s in found_frame:   
                    # 2 bones leg type 1, backup c_thigh_b rot first
                    if _s in c_thigh_b_rots_dict:
                        restore_c_thigh_b_rots(f, _s)
                    # snap
                    ik_to_fk_leg(armature, _s, add_keyframe=True)


def ik_to_fk_leg(rig, side, add_keyframe=False):
    thigh_b_fk = get_pose_bone(fk_leg[5]+side)
    thigh_fk = get_pose_bone(fk_leg[0]+side)
    leg_fk = get_pose_bone(fk_leg[1]+side)
    foot_fk = get_pose_bone(fk_leg[2]+side)
    toes_fk = get_pose_bone(fk_leg[3]+side)    
    
    thigh_ik = get_pose_bone(ik_leg[0]+side)
    leg_ik = get_pose_bone(ik_leg[1]+side)  
    foot_ik = get_pose_bone(ik_leg[2]+side)
    pole_ik = get_pose_bone(ik_leg[3]+side)
    toes_ik = get_pose_bone(ik_leg[4]+side)
    foot_01 = get_pose_bone(ik_leg[5]+side)
    foot_roll = get_pose_bone(ik_leg[6]+side)
    toes_pivot = get_pose_bone(ik_leg[9]+side)
    ik_offset = get_pose_bone(ik_leg[10]+side)
    ik_pivot = get_pose_bone(ik_leg[13]+side)
    c_leg_ik3 = get_pose_bone(ik_leg[12]+side)
    c_thigh_ik = get_pose_bone(ik_leg[8]+side)
    c_thigh_b = get_pose_bone(ik_leg[11]+side)
    
    if c_leg_ik3:# 3 Bones Leg Type 2
        # Snap Stretch values
        soft_ik = 'leg_softik' in foot_ik.keys()
        
        if soft_ik == False:
            foot_ik['stretch_length'] = foot_fk['stretch_length']
        else:
            soft_ik_fac = foot_ik['stretch_length'] / (thigh_ik.length+leg_ik.length)       
            foot_ik['stretch_length'] = soft_ik_fac * (thigh_fk.length+leg_fk.length)
            
        # reset IK foot_01, toes_pivot, ik_offset, foot_roll
        foot_01.rotation_euler = [0,0,0]
        
        if toes_pivot:
            toes_pivot.rotation_euler = toes_pivot.location = [0,0,0]
        if ik_offset:
            ik_offset.rotation_euler = ik_offset.location = [0,0,0]
        if ik_pivot:
            ik_pivot.rotation_euler = ik_pivot.location = [0,0,0]
        
        foot_roll.location[0] = 0.0
        foot_roll.location[2] = 0.0
        
        # Snap Toes
        toes_ik.rotation_euler= toes_fk.rotation_euler
        toes_ik.scale = toes_fk.scale
        
        # Child Of constraint or parent cases
        constraint = None
        bparent_name = ""
        parent_type = ""
        valid_constraint = True

        if len(foot_ik.constraints):
            for c in foot_ik.constraints:
                if not c.mute and c.influence > 0.5 and c.type == 'CHILD_OF':
                    if c.target:
                        #if bone
                        if c.target.type == 'ARMATURE':
                            bparent_name = c.subtarget
                            parent_type = "bone"
                            constraint = c
                        #if object
                        else:
                            bparent_name = c.target.name
                            parent_type = "object"
                            constraint = c


        if constraint != None:
            if parent_type == "bone":
                if bparent_name == "":
                    valid_constraint = False

        # Snap Foot
        if constraint and valid_constraint:
            if parent_type == "bone":
                bone_parent = get_pose_bone(bparent_name)
                foot_ik.matrix = bone_parent.matrix_channel.inverted() @ foot_fk.matrix
            if parent_type == "object":
                rig = bpy.data.objects[bparent_name]
                foot_ik.matrix = constraint.inverse_matrix.inverted() @ rig.matrix_world.inverted() @ foot_fk.matrix

        else:
            foot_ik.matrix = foot_fk.matrix.copy()
        
        # reset c_thigh_ik angle
        c_thigh_ik.rotation_euler[1] = 0.0
        
        # udpate
        bpy.context.view_layer.update()  
        
        # Snap Pole
        pole_dist = 1.0
        pole_height = 1.0
        foot_ref = get_data_bone("foot_ref"+side)
        if foot_ref:
            if "ik_pole_distance" in foot_ref.keys():
                pole_dist = foot_ref["ik_pole_distance"]
            if 'three_bones_leg_ik_height' in foot_ref.keys():
                pole_height = foot_ref['three_bones_leg_ik_height']
            
        pole_dist *= 2.0

        pole_rot = pole_ik.rotation_euler.copy()# pole rot should be preserved ideally (but does not alter the pose)
        
        # for 3 bones IK, the leg_fk rotation needs to be reset before evaluating the IK pole angle
        # but this leads to incorrect pole height... TODO, see if it can be improved
        leg_fk_rot = leg_fk.rotation_euler.copy()
        leg_fk.rotation_euler = [0,0,0]
        update_transform()

        pole_pos = get_ik_pole_pos(thigh_fk, leg_fk, pole_dist, three_bones_leg=True, thighb=get_pose_bone('c_thigh_ik'+side), pole_h=pole_height)
        pole_mat = Matrix.Translation(pole_pos)
        snap_bone_matrix(pole_ik, pole_mat, updt=False)
        #compensate_ik_pole_position(thigh_fk, leg_fk, thigh_ik, leg_ik, pole_ik)
        leg_fk.rotation_euler = leg_fk_rot
        pole_ik.rotation_euler = pole_rot
     
        # udpate hack
        update_transform()
        
        # snap c_leg_ik3
        leg_fk_h_name = 'leg_fk_h'+side
        leg_fk_h = get_pose_bone(leg_fk_h_name)
        snap_rot(c_leg_ik3, leg_fk_h)
        c_leg_ik3.location = [0,0,0]
        #c_leg_ik3.rotation_euler[0] = c_leg_ik3.rotation_euler[1] = 0.0
        c_leg_ik3.scale = [1,1,1]
        
         # Switch prop
        foot_ik['ik_fk_switch'] = 0.0

        # udpate hack
        update_transform()

        #insert key if autokey enable
        if bpy.context.scene.tool_settings.use_keyframe_insert_auto or add_keyframe:
            # switch
            foot_ik.keyframe_insert(data_path='["ik_fk_switch"]')
            #ik chain
            foot_ik.keyframe_insert(data_path='["stretch_length"]')        
            foot_ik.keyframe_insert(data_path='["auto_stretch"]')
            keyframe_pb_transforms(c_leg_ik3, loc=False, scale=False)
            keyframe_pb_transforms(foot_ik)
            keyframe_pb_transforms(foot_01, loc=False, scale=False)
            keyframe_pb_transforms(foot_roll, rot=False, scale=False)
            keyframe_pb_transforms(toes_ik, loc=False)    
            keyframe_pb_transforms(pole_ik, rot=False, scale=False)
            if toes_pivot:
                keyframe_pb_transforms(toes_pivot, scale=False)
            if ik_offset:
                keyframe_pb_transforms(ik_offset)
            if ik_pivot:
                keyframe_pb_transforms(ik_pivot)
            

            #fk chain        
            foot_fk.keyframe_insert(data_path='["stretch_length"]')
            keyframe_pb_transforms(thigh_b_fk, loc=False, scale=False)
            keyframe_pb_transforms(foot_fk, loc=False)
            keyframe_pb_transforms(thigh_fk, loc=False, scale=False)
            keyframe_pb_transforms(leg_fk, loc=False, scale=False)
            keyframe_pb_transforms(toes_fk, loc=False)
            
    else:
        # Snap Stretch
        soft_ik = 'leg_softik' in foot_ik.keys()
        
        if soft_ik == False:
            foot_ik['stretch_length'] = foot_fk['stretch_length']
        else:
            soft_ik_fac = foot_ik['stretch_length'] / (thigh_ik.length+leg_ik.length)       
            foot_ik['stretch_length'] = soft_ik_fac * (thigh_fk.length+leg_fk.length)

        # reset IK foot_01, toes_pivot, ik_offset, foot_roll
        foot_01.rotation_euler = [0,0,0]
        
        if toes_pivot:
            toes_pivot.rotation_euler = toes_pivot.location = [0,0,0]
        if ik_offset:
            ik_offset.rotation_euler = ik_offset.location = [0,0,0]
        if ik_pivot:
            ik_pivot.rotation_euler = ik_pivot.location = [0,0,0]
        

        foot_roll.location[0] = 0.0
        foot_roll.location[2] = 0.0

        # reset custom pole angle if any
        if c_thigh_ik:
            c_thigh_ik.rotation_euler[1] = 0.0
        
        # save the c_thigh_b matrix if any
        if c_thigh_b:
            c_thigh_b_matrix = c_thigh_b.matrix.copy()

        # Snap Toes
        toes_ik.rotation_euler= toes_fk.rotation_euler.copy()
        toes_ik.scale = toes_fk.scale.copy()
        
        # Child Of constraint or parent cases
        constraint = None
        bparent_name = ""
        parent_type = ""
        valid_constraint = True

        if len(foot_ik.constraints):
            for c in foot_ik.constraints:
                if not c.mute and c.influence > 0.5 and c.type == 'CHILD_OF':
                    if c.target:
                        #if bone
                        if c.target.type == 'ARMATURE':
                            bparent_name = c.subtarget
                            parent_type = "bone"
                            constraint = c
                        #if object
                        else:
                            bparent_name = c.target.name
                            parent_type = "object"
                            constraint = c


        if constraint != None:
            if parent_type == "bone":
                if bparent_name == "":
                    valid_constraint = False

        # Snap Foot
        if constraint and valid_constraint:
            if parent_type == "bone":
                bone_parent = get_pose_bone(bparent_name)
                foot_ik.matrix = bone_parent.matrix_channel.inverted() @ foot_fk.matrix
            if parent_type == "object":
                rig = bpy.data.objects[bparent_name]
                foot_ik.matrix = constraint.inverse_matrix.inverted() @ rig.matrix_world.inverted() @ foot_fk.matrix

        else:
            foot_ik.matrix = foot_fk.matrix.copy()
        
        # udpate
        bpy.context.view_layer.update()    
        
        # Snap Pole
        pole_dist = 1.0
        pole_height = 1.0
        foot_ref = get_data_bone("foot_ref"+side)
        if foot_ref:
            if "ik_pole_distance" in foot_ref.keys():
                pole_dist = foot_ref["ik_pole_distance"]
            if 'three_bones_leg_ik_height' in foot_ref.keys():
                pole_height = foot_ref['three_bones_leg_ik_height']

        # double the pole dist if three bones leg type 1
        if c_thigh_b and "three_bones_ik" in foot_ik.keys():
            pole_dist *= 2.0
        
        pole_rot = pole_ik.rotation_euler.copy()# should be preserved
        
        if c_thigh_b and "three_bones_ik" in foot_ik.keys():# 3 Bones Leg Type 1
            pole_pos = get_ik_pole_pos(thigh_fk, leg_fk, pole_dist, three_bones_leg=True, thighb=c_thigh_b, pole_h=pole_height)# higher pole if 3 bones leg type 1
        else:
            pole_pos = get_ik_pole_pos(thigh_fk, leg_fk, pole_dist)
        pole_mat = Matrix.Translation(pole_pos)
        snap_bone_matrix(pole_ik, pole_mat)    
        compensate_ik_pole_position(thigh_fk, leg_fk, thigh_ik, leg_ik, pole_ik)
        
        pole_ik.rotation_euler = pole_rot
     
        # udpate hack
        update_transform()
        
         # Switch prop
        foot_ik['ik_fk_switch'] = 0.0

        # udpate hack
        update_transform()

        # Restore c_thigh_b matrix if any
        if c_thigh_b:
            c_thigh_b.matrix = c_thigh_b_matrix.copy()

        #update hack
        update_transform()

        #insert key if autokey enable
        if bpy.context.scene.tool_settings.use_keyframe_insert_auto or add_keyframe:
            #ik chain
            foot_ik.keyframe_insert(data_path='["ik_fk_switch"]')
            foot_ik.keyframe_insert(data_path='["stretch_length"]')        
            foot_ik.keyframe_insert(data_path='["auto_stretch"]')
            
            if c_thigh_b:
                keyframe_pb_transforms(c_thigh_b)
            keyframe_pb_transforms(foot_ik)
            foot_01.keyframe_insert(data_path="rotation_euler")
            foot_roll.keyframe_insert(data_path="location")
            keyframe_pb_transforms(toes_ik, loc=False)        
            pole_ik.keyframe_insert(data_path="location")
            
            #ik controller if any
            if c_thigh_ik:            
                c_thigh_ik.keyframe_insert(data_path="rotation_euler", index=1)
                
            if toes_pivot:
                keyframe_pb_transforms(toes_pivot, scale=False)
            if ik_offset:
                keyframe_pb_transforms(ik_offset)
            if ik_pivot:
                keyframe_pb_transforms(ik_pivot)

            #fk chain        
            foot_fk.keyframe_insert(data_path='["stretch_length"]')
            keyframe_pb_transforms(foot_fk, loc=False)
            keyframe_pb_transforms(thigh_fk, loc=False, scale=False)
            keyframe_pb_transforms(leg_fk, loc=False, scale=False)
            keyframe_pb_transforms(toes_fk, loc=False)
           
        
    # change FK to IK foot selection, if selected
    #if foot_fk.bone.select and not add_keyframe:
    if is_pbone_selected(foot_fk) and not add_keyframe:
        select_pbone(foot_ik)
        rig.data.bones.active = foot_ik.bone
        select_pbone(foot_fk, state=False)


def get_ik_pole_pos(b1, b2, dist, invert=False, three_bones_leg=False, thighb=None, pole_h=1.0):
    plane_normal = (b1.head - b2.tail)
    midpoint = (b1.head + b2.tail) * 0.5
    prepole_dir = b2.head - midpoint
    pole_pos = b2.head + prepole_dir.normalized()

    p = b2.head.copy()
    if three_bones_leg:# if 3 bones leg, set the pole higher, taking into account the full 3 bones length
        # old alignment, comment out
        # vec = (thighb.head-p).magnitude * pole_h
        # p += plane_normal.normalized() * vec * 0.5
        p += plane_normal.normalized() * 0.2 * pole_h
            
    pole_pos = project_point_onto_plane(pole_pos, p, plane_normal)
    
    pole_pos = b2.head + ((pole_pos - b2.head).normalized() * (b2.head - b1.head).magnitude * dist)
    #print(br)
    return pole_pos
    
        
def compensate_ik_pole_position(fk1, fk2, ik1, ik2, pole):
    #print("Compensate IK pole angle check")
    angle_offset = get_ik_fk_angle_offset(fk1, fk2, ik1, ik2, pole)
    i = 0
    dir = 1
    iter_max = 6
    error_rate = 0.005
    #print("Angle offset", angle_offset)
    
    while (angle_offset > error_rate and i < iter_max):
        #print("Compensate IK Pole angle...", angle_offset)
        axis = (ik2.tail-ik1.head)
        origin = (fk2.tail + fk1.head) / 2
        pole_rotated = _rotate_point(pole.head, angle_offset*dir, axis, origin)        
        snap_bone_matrix(pole, Matrix.Translation(pole_rotated))
        new_angle = get_ik_fk_angle_offset(fk1, fk2, ik1, ik2, pole)
        if new_angle > angle_offset:# wrong direction!            
            dir *= -1
        angle_offset = new_angle
        i += 1   
        #print("New offset value:", angle_offset)
        
        

def get_ik_fk_angle_offset(fk1, fk2, ik1, ik2, pole):
    def signed_angle(vector_u, vector_v, normal):
        normal = normal.normalized()
        a = vector_u.angle(vector_v)
        if vector_u.magnitude != 0.0 and vector_v.magnitude != 0.0 and normal.magnitude != 0.0:
            if vector_u.cross(vector_v).magnitude != 0.0:      
                if vector_u.cross(vector_v).angle(normal) < 1:
                    a = -a
        return a
    
    midpoint = (fk2.tail + fk1.head) / 2
    vec1 = fk2.head - midpoint
    vec2 = ik2.head - midpoint
    pole_normal = (ik2.tail - ik1.head).cross(pole.head - ik1.head)
    angle = signed_angle(vec1, vec2, pole_normal)
    return angle
    
    
def _bake_pole_parent(self, space_target=None):
    armature = bpy.context.active_object
    c_pole_name = 'c_'+self.bone_type+'_pole'+self.side
    c_pole = get_pose_bone(c_pole_name)
    
    # store original state for each frame
    pole_parent_states = {}
    pole_locs = {}
    
    for f in range(self.frame_start, self.frame_end +1):
        bpy.context.scene.frame_set(f)
        pole_parent_states[f] = c_pole['pole_parent']
        pole_locs[f] = c_pole.location.copy()
    
    # bake all frames
    if self.one_key_per_frame:
        for f in range(self.frame_start, self.frame_end +1):      
            bpy.context.scene.frame_set(f)   
            # set back original states for this frame
            c_pole['pole_parent'] = pole_parent_states[f]            
            c_pole.location = pole_locs[f]
            update_transform()
            # snap
            _snap_pole(armature, self.side, self.bone_type, space_target=space_target)
    
    else:# bake only existing keyframes
        # collect frames that have keyframes
        frames_idx = []

        fc_start_dp = 'pose.bones["'+c_pole_name+'"].'
        
        #print("Gather keyframes...")
        for fc in get_action_fcurves(armature.animation_data.action):
            if fc.data_path.startswith(fc_start_dp):
                for keyf in fc.keyframe_points:
                    if keyf.co[0] >= self.frame_start and keyf.co[0] <= self.frame_end:
                        if not keyf.co[0] in frames_idx:
                            #print("  append", keyf.co[0])
                            frames_idx.append(keyf.co[0])
        
        for f in frames_idx:
            print('Bake frame', f)
            bpy.context.scene.frame_set(int(f))    
            # set back original states for this frame
            c_pole['pole_parent'] = pole_parent_states[f]     
            c_pole.location = pole_locs[f]
            update_transform()
            # snap
            _snap_pole(armature, self.side, self.bone_type, space_target=space_target)
    
    
def _snap_pole(ob, side, bone_type, space_target=None):
    pole = get_pose_bone('c_'+bone_type+'_pole'+side)
    rig = bpy.context.active_object
    
    # disable mirror
    mirror_state = rig.pose.use_mirror_x
    rig.pose.use_mirror_x = False
    
    if pole:     
        if 'pole_parent' in pole.keys():
            # save the pole matrix
            pole_mat = pole.matrix.copy()

            # switch the property
            if space_target == None:
                pole['pole_parent'] = 1 if pole['pole_parent'] == 0 else 0
            else:
                if space_target == 'GLOBAL':
                    pole["pole_parent"] = 0
                elif space_target == 'LOCAL':
                    pole['pole_parent'] = 1
                elif space_target == 'SMART':
                    pole['pole_parent'] = 2
                
            #update hack
            update_transform()
            
            # snap
            snap_bone_matrix(pole, pole_mat, updt=False)                  
                    
            #insert keyframe if autokey enable
            if bpy.context.scene.tool_settings.use_keyframe_insert_auto:
                pole.keyframe_insert(data_path='["pole_parent"]')
                pole.keyframe_insert(data_path="location")

        else:
            print("No pole_parent poprerty found")

    else:
        print("No c_leg_pole found")
        
    # restore mirror
    rig.pose.use_mirror_x = mirror_state
       
       
#   IK FK Spline
def bake_ik_to_fk_spline(self):
    print('Bake IK to FK Spline')
    armature = bpy.context.active_object
    scn = bpy.context.scene
    
    if self.one_key_per_frame:# bake all frames
        for f in range(self.frame_start, self.frame_end +1):
            bpy.context.scene.frame_set(f)      
            ik_to_fk_spline(armature, self.spline_name, self.side, add_keyframe=True)
    
    else:# bake only existing keyframes
        # collect frames that have keyframes
        spline_fk_ctrl = get_spline_ctrls(self.spline_name, self.side, masters=True, inters=True, add_ik_others=True)[0]
       
        frames_idx = []
        
        for bname in spline_fk_ctrl:
            fc_start_dp = 'pose.bones["'+bname+'"].'
            
            for fc in get_action_fcurves(armature.animation_data.action):
                if fc.data_path.startswith(fc_start_dp):
                    for keyf in fc.keyframe_points:
                        if keyf.co[0] >= self.frame_start and keyf.co[0] <= self.frame_end:
                            if not keyf.co[0] in frames_idx:
                                frames_idx.append(keyf.co[0])
            
        for f in frames_idx:
            bpy.context.scene.frame_set(int(f))
            ik_to_fk_spline(armature, self.spline_name, self.side, add_keyframe=True)      
            
            
def bake_fk_to_ik_spline(self):
    print('Bake FK to IK Spline')
    armature = bpy.context.active_object
    scn = bpy.context.scene
    
    if self.one_key_per_frame:# bake all frames
        for f in range(self.frame_start, self.frame_end +1):
            bpy.context.scene.frame_set(f)      
            fk_to_ik_spline(armature, self.spline_name, self.side, add_keyframe=True)
    
    else:# bake only existing keyframes
        # collect frames that have keyframes
        spline_ik_ctrl = get_spline_ctrls(self.spline_name, self.side, masters=True, inters=True, add_ik_others=True)[1]
       
        frames_idx = []
        
        for bname in spline_ik_ctrl:
            fc_start_dp = 'pose.bones["'+bname+'"].'
            
            for fc in get_action_fcurves(armature.animation_data.action):
                if fc.data_path.startswith(fc_start_dp):
                    for keyf in fc.keyframe_points:
                        if keyf.co[0] >= self.frame_start and keyf.co[0] <= self.frame_end:
                            if not keyf.co[0] in frames_idx:
                                frames_idx.append(keyf.co[0])
            
        for f in frames_idx:
            bpy.context.scene.frame_set(int(f))
            fk_to_ik_spline(armature, self.spline_name, self.side, add_keyframe=True)                
    
    
    
def get_spline_ctrls(spline_name, side, masters=False, inters=False, add_ik_others=False):
    c_fk_names = []
    c_ik_names = []
    
    if add_ik_others:
        names = ['c_'+spline_name+'_tip'+side, 'c_'+spline_name+'_curvy'+side, 'c_'+spline_name+'_root'+side]
        for n in names:
            pb = get_pose_bone(n)
            if pb:
                c_ik_names.append(n)
        
    
    for i in range(1, 1024):
        stri = '%02d' % i
        # get IK ctrl
        c_ik_name = 'c_'+spline_name+'_'+stri+side
        c_ik_pb = get_pose_bone(c_ik_name)
        if c_ik_pb:
            c_ik_names.append(c_ik_name)
            
            # get FK ctrl
            c_fk_name = 'c_'+spline_name+'_fk_'+stri+side
            c_fk_pb = get_pose_bone(c_fk_name)
            if c_fk_pb:
                c_fk_names.append(c_fk_name)
            else:# reached the tip
                break
                    
            if inters:
                c_ik_inter_name = 'c_'+spline_name+'_inter_'+stri+side
                c_ik_inter_pb = get_pose_bone(c_ik_inter_name)
                if c_ik_inter_pb:
                    c_ik_names.append(c_ik_inter_name)
                
        else:# reached the tip
            break
            
    if masters:
        for i in range(1, 1024):
            stri = '%02d' % i
            c_ik_mas_name = 'c_'+spline_name+'_master_'+stri+side
            c_ik_mas_pb = get_pose_bone(c_ik_mas_name)
            if c_ik_mas_pb:
                c_ik_names.append(c_ik_mas_name)
            else:#reached tip
                break
                
            c_fk_name_mas = 'c_'+spline_name+'_fk_master_'+stri+side
            c_fk_mas_pb = get_pose_bone(c_fk_name_mas)
            if c_fk_mas_pb:
                c_fk_names.append(c_fk_name_mas)
            
    return c_fk_names, c_ik_names


def fk_to_ik_spline(obj, spline_name, side, add_keyframe=False):
    c_spline_root = get_pose_bone('c_'+spline_name+'_root'+side)    
    scn = bpy.context.scene
    
    #  collect indiv controllers    
    c_fk_names, c_ik_names = get_spline_ctrls(spline_name, side)
    c_fk_names_master, c_ik_names_master = get_spline_ctrls(spline_name, side, masters=True)

    # collect def bones
    def_names = []
        
    for i in range(1, 1024):
        id = '%02d' % i        
        def_name = spline_name+'_def_'+id+side
        def_pb = get_pose_bone(def_name)
        if def_pb:
            def_names.append(def_name)        
        else:
            break
    
    # reset FK masters    
    spline_ik_type = '1'
    
    for i in range(1, 1024):
        id = '%02d' % i           
        c_fk_name = 'c_'+spline_name+'_fk_master_'+id+side
        c_fk_pb = get_pose_bone(c_fk_name)
        if c_fk_pb:
            zero_out_pb(c_fk_pb) 
        else:
            break
            
        # Spline IK type?
        # look for IK masters. If none, this is a Spline IK type 1
        if spline_ik_type == '1':
            c_ik_name = 'c_'+spline_name+'_master_'+id+side
            c_ik_pb = get_pose_bone(c_ik_name)
            if c_ik_pb:
                spline_ik_type = '2'
    
    #   snap
    fk_tip = None
    
    for i, c_fk_name in enumerate(c_fk_names):
        c_fk_pb = get_pose_bone(c_fk_name)
        if i > len(c_ik_names)-1:
            print('Missing Spline IK controller: index '+i)
            continue

        if spline_ik_type == '2':
            c_ik_pb = get_pose_bone(c_ik_names[i])
            c_fk_pb.matrix = c_ik_pb.matrix.copy()

        elif spline_ik_type == '1':# basic spline IK, need to copy from the deform chain for correct bones rotation
            def_pb = get_pose_bone(def_names[i])
            c_fk_pb.matrix = def_pb.matrix.copy()
            
        # chain stretch support, only scale the first bone
        if i != 0:
            c_fk_pb.scale = [1,1,1]
        
        fk_tip = c_fk_pb
        
        update_transform()
        
    
    # Snap tail if any
    tail_fk_name = 'c_'+spline_name+'_fk_tail'+side
    tail_fk_pb = get_pose_bone(tail_fk_name)
    tail_ik_name = 'c_'+spline_name+'_tail'+side
    tail_ik = get_pose_bone(tail_ik_name)
    
    if tail_fk_pb and tail_ik:
        # must be connected to the tail of the last ctrl FK
        loc = fk_tip.tail.copy()
        l, rot, scale = tail_ik.matrix.decompose()
        tail_fk_pb.matrix = Matrix.LocRotScale(loc, rot, scale)
        
        
    # switch
    c_spline_root['ik_fk_switch'] = 1.0
            
    #insert key if autokey enable    
    if bpy.context.scene.tool_settings.use_keyframe_insert_auto or add_keyframe:
        
        c_spline_root.keyframe_insert(data_path='["ik_fk_switch"]')
 
        for c_fk_name in c_fk_names_master:
            c_fk_pb = get_pose_bone(c_fk_name)
            keyframe_pb_transforms(c_fk_pb, scale=False)

        for c_ik_name in c_ik_names:
            c_ik_pb = get_pose_bone(c_ik_name)
            keyframe_pb_transforms(c_ik_pb, scale=False)
    
    # update hack
    update_transform()
        
        
    # change IK to FK foot selection    
    bpy.ops.pose.select_all(action='DESELECT')
    c_fk_pb = get_pose_bone(c_fk_names[0])
    select_pbone(c_fk_pb)
    obj.data.bones.active = c_fk_pb.bone

    
def ik_to_fk_spline(obj, spline_name, side, add_keyframe=False):
    c_spline_root = get_pose_bone('c_'+spline_name+'_root'+side)
    scn = bpy.context.scene
    
    # collect masters
    c_fk_master_names = []
    c_ik_master_names = []
    
    spline_ik_type = '1'
    
    # get IK, FK ctrl, spline type
    for i in range(1, 1024):
        id = '%02d' % i
        # IK
        c_ik_name = 'c_'+spline_name+'_master_'+id+side
        c_ik_pb = get_pose_bone(c_ik_name)
        if c_ik_pb:
            c_ik_master_names.append(c_ik_name)
            #FK
            c_fk_name = 'c_'+spline_name+'_fk_master_'+id+side
            c_fk_pb = get_pose_bone(c_fk_name)
            if c_fk_pb:
                c_fk_master_names.append(c_fk_name) 

            # Spline IK type?
            # look for IK masters. If none, this is a Spline IK type 1
            if spline_ik_type == '1':           
                spline_ik_type = '2'
                
        else:
            break
    
    if spline_ik_type == '2' and len(c_fk_master_names)+1 != len(c_ik_master_names):
        print('IK and FK chains have different amount of master controllers, cannot snap')
        c_spline_root['ik_fk_switch'] = 0.0
        update_transform()
        return
    
    # collect inters  
    c_ik_inter_names = []
    
    for i in range(1, 1024):
        id = '%02d' % i
        # get IK ctrl
        c_ik_name = 'c_'+spline_name+'_inter_'+id+side
        c_ik_pb = get_pose_bone(c_ik_name)
        if c_ik_pb:
            c_ik_inter_names.append(c_ik_name)              
        else:
            break
            
    # collect individual controllers
    c_fk_names = []
    c_ik_names = []
    
    for i in range(1, 1024):
        id = '%02d' % i
        # get IK ctrl
        c_ik_name = 'c_'+spline_name+'_'+id+side
        c_ik_pb = get_pose_bone(c_ik_name)
        if c_ik_pb:
            c_ik_names.append(c_ik_name)
            # get FK ctrl
            c_fk_name = 'c_'+spline_name+'_fk_'+id+side
            c_fk_pb = get_pose_bone(c_fk_name)
            if c_fk_pb:
                c_fk_names.append(c_fk_name)
            else:
                break            
        else:
            break

    
    # if Spline type 1, snap first the curvy and tip controller
    tip_name = 'c_'+spline_name+'_tip'+side
    
    if spline_ik_type == '1':
        # tip
        c_tip_pb = get_pose_bone(tip_name)
        
        #   get the tail of the last FK bone
        c_fk_pb = get_pose_bone(c_fk_names[len(c_fk_names)-1])
        tail_mat = Matrix.Translation(c_fk_pb.tail)
        c_tip_pb.matrix = tail_mat
        
        update_transform()
        
        # curvy
        curvy_name = 'c_'+spline_name+'_curvy'+side
        c_curvy = get_pose_bone(curvy_name)
        
        # get the ctrl the most influenced by the curvy constraint
        # not ideal, see if a better snap method can be found later?
        max_inf = 0.0
        mid_pb = None
        
        for c_ik_name in c_ik_names:
            c_ik = get_pose_bone(c_ik_name)
            for cns in c_ik.constraints:
                if cns.type == 'COPY_TRANSFORMS':
                    if cns.subtarget == curvy_name:
                        if max_inf < cns.influence:
                            max_inf = cns.influence
                            mid_pb = c_ik
                            
        if mid_pb:
            def get_name_idx(name):    
                for i in name.split('_'):  
                    i = i.split('.')[0]
                    if i.isdigit() and len(i) == 2:            
                        return int(i)  
            
            idx = get_name_idx(mid_pb.name)
            s_idx = '%02d' % idx
            c_fk_mid = get_pose_bone('c_'+spline_name+'_fk_'+s_idx+side)
            
            if c_fk_mid:
                c_curvy.matrix = c_fk_mid.matrix.copy()
                c_curvy.scale = [1,1,1]                
        
        update_transform()
    
    
    # snap tip
    if spline_ik_type == '2':
        c_spline_tip_name = 'c_'+spline_name+'_tip'+side
        c_spline_tip = get_pose_bone(c_spline_tip_name)
        
        if c_spline_tip:
            c_fk_tip_pb = get_pose_bone(c_fk_names[len(c_fk_names)-1])            
            tail_mat = Matrix.Translation(c_fk_tip_pb.tail)
            loc, rot, scale = c_fk_tip_pb.matrix.decompose()
            mat_def = Matrix.LocRotScale(c_fk_tip_pb.tail, rot, scale)
            c_spline_tip.matrix = mat_def
    
    # snap masters
    for i, c_ik_master_name in enumerate(c_ik_master_names):
        c_ik_master_pb = get_pose_bone(c_ik_master_name) 
        
        if i == len(c_ik_master_names)-1:# last, use the tail of the FK ctrl bone
            c_fk_tip_pb = get_pose_bone(c_fk_names[len(c_fk_names)-1])
            tail_mat = Matrix.Translation(c_fk_tip_pb.tail)
            c_ik_master_pb.matrix = tail_mat
        else:
            c_fk_master_name = c_fk_master_names[i]
            c_fk_master_pb = get_pose_bone(c_fk_master_name)
            c_ik_master_pb.matrix = c_fk_master_pb.matrix.copy()
            
        # rot and scale not supported on masters, zero out
        c_ik_master_pb.scale = [1,1,1]
        c_ik_master_pb.rotation_euler = [0,0,0]
        c_ik_master_pb.rotation_quaternion = [1,0,0,0]
        update_transform()
        
    
    # Snap Inters (T2)/ Main controllers (T1)
    # base snapping
    for i in range(0, len(c_fk_names)):
        id = i+1
        stri = '%02d' % id
        if id > len(c_fk_names):
            continue
        c_name = ''
        if spline_ik_type == '1':
            c_name = 'c_'+spline_name+'_'+stri+side
        if spline_ik_type == '2':
            c_name = 'c_'+spline_name+'_inter_'+stri+side
        c_fk_name = 'c_'+spline_name+'_fk_'+stri+side
        c_pb = get_pose_bone(c_name)
        c_fk_pb = get_pose_bone(c_fk_name)
        
        if spline_ik_type == '1':# Child Of constraints don't require iterative approach
            set_bone_matrix_cns_simple(c_pb, c_fk_pb.matrix)
        if spline_ik_type == '2':# Copy Transforms with Mix Mode: Before requires iterative approach
            set_bone_matrix_cns_iter(c_pb, c_fk_pb.matrix, iter_max=10)

    # refine to reverse fit the curve shape
    refine = True
    if refine:
        iter_max = scn.arp_spline_snap_iter_max
        
        for k in range(0, 2):
            #print('PASS', k)
            
            for i in range(0, len(c_fk_names)):
                id = i+1
                if id < 2:# need at least 2 bones to evaluate the curviness
                    continue
                if id > len(c_fk_names):
                    continue
                #print('id', id)
                stri = '%02d' % id
                pstri = '%02d' % (id-1)
                c_name = ''
                if spline_ik_type == '1':
                    c_name = 'c_'+spline_name+'_'+stri+side
                if spline_ik_type == '2':
                    c_name = 'c_'+spline_name+'_inter_'+stri+side
                c_pb = get_pose_bone(c_name)
                c_fk_name = 'c_'+spline_name+'_fk_'+stri+side
                c_fk_prev_name = 'c_'+spline_name+'_fk_'+pstri+side
                def_name = ''
                if spline_ik_type == '1':
                    def_name = spline_name+'_'+stri+side
                elif spline_ik_type == '2':
                    def_name = 'c_'+spline_name+'_'+stri+side                
                
                fk = get_pose_bone(c_fk_name)
                def_bone = get_pose_bone(def_name)
                fk_prev = get_pose_bone(c_fk_prev_name)
                
                last_push_fac = None
                prev_mat = c_pb.matrix.copy()
                prev_vec_diff = (fk.head - def_bone.head)
                prec = scn.arp_spline_snap_precision-1
                
                # the refine pass does not support stretch for now
                if fk.scale != Vector((1,1,1)) and k == 1:
                    print('FK scaled , skip', fk.scale)
                    continue
                
                for j in range(0, iter_max):                    
                    # refine iteratively                
                    if k == 0:
                        # offset by the midpoint vector first for
                        midpoint = (fk_prev.head + fk.tail)*0.5
                        vec_dir = (fk.head - midpoint)
                        vec2 = (def_bone.head-midpoint)                        
                        push_fac = (fk.head-midpoint).magnitude / vec2.magnitude if vec2.magnitude != 0.0 else 0.0
                        if push_fac < 1:
                            vec_dir *= -1
                        push_fac *= 0.1
                        #print('push_fac', push_fac)
                        
                        if last_push_fac:
                            if last_push_fac < 0 and push_fac > 0:
                                break
                            if last_push_fac > 0 and push_fac < 0:
                                break
                        else:
                            last_push_fac = push_fac
                        
                        vec_diff = vec_dir * push_fac
                        mat_transl = Matrix.Translation(vec_diff).to_4x4()
                        mat_tar = mat_transl @ c_pb.matrix
                        
                    else:
                        # refine by using the direct vector
                        vec_diff = fk.head - def_bone.head                        
                        mat_transl = Matrix.Translation(vec_diff).to_4x4()
                        mat_tar = mat_transl @ c_pb.matrix
                    
                    set_bone_matrix_cns_iter(c_pb, mat_tar, iter_max=iter_max)            
                    
                    if prev_vec_diff and k == 1:
                        if (fk.head - def_bone.head).magnitude > prev_vec_diff.magnitude and prev_mat:# cannot snap compensate, probably due to stretched chain, skip
                            set_bone_matrix_cns_iter(c_pb, prev_mat, iter_max=iter_max) 
                            print(c_pb.name, 'could not refine, skip')
                            break
                    prev_vec_diff = (fk.head - def_bone.head)
                    
                    if prev_mat:
                        compare = compare_mat(c_pb.matrix, prev_mat, prec)
                        if compare:# snapped tight, exit
                            print(c_pb.name, 'Refine: Matched with', id, 'iterations, prec =', prec)                
                            break
                    prev_mat = c_pb.matrix.copy()
                    
                c_pb.scale = [1,1,1]
                
                
    # Snap tail if any
    tail_fk_name = 'c_'+spline_name+'_fk_tail'+side
    tail_fk_pb = get_pose_bone(tail_fk_name)
    tail_ik_name = 'c_'+spline_name+'_tail'+side
    tail_ik = get_pose_bone(tail_ik_name)
    
    if tail_fk_pb and tail_ik:
        print('SNAP IK TAIL')
        tail_ik.matrix = tail_fk_pb.matrix.copy()
        
                
    # Snap indiv. controllers
    # it remains optional, because leads to to buggy behavior when manipulating the IK spline  
    if spline_ik_type == '2':
        if scn.arp_spline_snap_indiv:
            for i, c_ik_name in enumerate(c_ik_names):
                if i >= len(c_fk_names):
                    continue
                    
                c_ik_pb = get_pose_bone(c_ik_name)
                c_fk_name = c_fk_names[i]
                c_fk_pb = get_pose_bone(c_fk_name)
                
                if len(c_ik_pb.constraints):
                    # disable indiv constraints
                    cns_states = []
                    for cns in c_ik_pb.constraints:
                        cns_states.append(cns.enabled)
                        cns.enabled = False
                        
                    update_transform()
                    
                    # apply target matrix
                    c_ik_pb.matrix = c_fk_pb.matrix.copy()
                    update_transform()
                    mat_no_cns = c_ik_pb.matrix.copy()
                    
                    # enable constraints
                    for ci, cns in enumerate(c_ik_pb.constraints):
                        cns.enabled = cns_states[ci]
                    
                    update_transform()
                    
                    # compensate constraints offset
                    mat_cns = c_ik_pb.matrix.copy()
                    mat_diff = mat_cns.inverted() @ mat_no_cns
                    c_ik_pb.matrix = mat_no_cns @ mat_diff                
                    update_transform()
                else:
                    c_ik_pb.matrix = c_fk_pb.matrix.copy()
                    
                # stretch/scale not supported, zero out
                c_ik_pb.scale = [1,1,1]       
                update_transform()

        else:
            # zero out individual controllers
            if spline_ik_type == '2':
                for i, c_ik_name in enumerate(c_ik_names):
                    c_ik_pb = get_pose_bone(c_ik_name)
                    zero_out_pb(c_ik_pb)
    
    
    update_transform()
        
    # switch
    c_spline_root['ik_fk_switch'] = 0.0

    update_transform()

    #insert key if autokey enable    
    if bpy.context.scene.tool_settings.use_keyframe_insert_auto or add_keyframe:
        c_spline_root.keyframe_insert(data_path='["ik_fk_switch"]')
        
        # FK indiv controllers
        for c_fk_name in (c_fk_names):
            c_fk_pb = get_pose_bone(c_fk_name)
            keyframe_pb_transforms(c_fk_pb)
        # FK masters
        for c_fk_name in (c_fk_master_names):
            c_fk_master_pb = get_pose_bone(c_fk_name)
            keyframe_pb_transforms(c_fk_master_pb)
        # IK masters
        for c_ik_name in (c_ik_master_names):
            c_ik_master_pb = get_pose_bone(c_ik_name)
            keyframe_pb_transforms(c_ik_master_pb)
        # IK inters
        for c_ik_name in (c_ik_inter_names):
            c_ik_inter_pb = get_pose_bone(c_ik_name)
            keyframe_pb_transforms(c_ik_inter_pb)
        # IK indiv
        for c_ik_name in (c_ik_names):
            c_ik_pb = get_pose_bone(c_ik_name)
            keyframe_pb_transforms(c_ik_pb)
        # Spline tip
        c_tip_pb = get_pose_bone(tip_name)
        keyframe_pb_transforms(c_tip_pb)
        
        if spline_ik_type == '1':
            # Spline curvy
            c_curvy_pb = get_pose_bone(curvy_name)
            if c_curvy_pb:
                keyframe_pb_transforms(c_curvy_pb)
            
    # change IK to FK foot selection    
    bpy.ops.pose.select_all(action='DESELECT')
    c_ik_pb = get_pose_bone(c_ik_names[0])
    select_pbone(c_ik_pb)
    obj.data.bones.active = c_ik_pb.bone
    
    # update hack
    update_transform()


def _switch_snap_pin(side, type):
    if type == "leg":
        c_leg_stretch = get_pose_bone("c_stretch_leg"+side)
        if c_leg_stretch == None:
            return

        c_leg_pin = get_pose_bone("c_stretch_leg_pin"+side)
        if c_leg_pin == None:
            return

        if c_leg_stretch["leg_pin"] == 0.0:
            c_leg_pin.matrix = c_leg_stretch.matrix
            c_leg_stretch["leg_pin"] = 1.0
        else:
            c_leg_stretch["leg_pin"] = 0.0
            c_leg_stretch.matrix = c_leg_pin.matrix

    if type == "arm":
        c_arm_stretch = get_pose_bone("c_stretch_arm"+side)
        if c_arm_stretch == None:
            return

        c_arm_pin = get_pose_bone("c_stretch_arm_pin"+side)
        if c_arm_pin == None:
            return

        if c_arm_stretch["elbow_pin"] == 0.0:
            c_arm_pin.matrix = c_arm_stretch.matrix
            c_arm_stretch["elbow_pin"] = 1.0
        else:
            c_arm_stretch["elbow_pin"] = 0.0
            c_arm_stretch.matrix =  c_arm_pin.matrix

   
def _bake_limb_lock(self):
    armature = bpy.context.active_object
    c_limb_fk_name = ard.arm_bones_dict['arm']['control_fk']+self.side if self.bone_type == 'arm' else ard.leg_bones_dict['upthigh']+self.side
    c_limb_fk = get_pose_bone(c_limb_fk_name)
    c_prop_bone_name = ard.arm_bones_dict['shoulder']['control']+self.side if self.bone_type == 'arm' else ard.leg_bones_dict['upthigh']+self.side
    c_prop_bone = get_pose_bone(c_prop_bone_name)
    prop_name = 'arm_lock' if self.bone_type == 'arm' else 'thigh_lock'
    
    # store original states for each frame
    limb_lock_states = {}
    limb_rots = {}    
    
    for f in range(self.frame_start, self.frame_end +1):
        bpy.context.scene.frame_set(f)
        limb_lock_states[f] = c_prop_bone[prop_name]
        limb_rots[f] = c_limb_fk.rotation_euler.copy(), c_limb_fk.rotation_quaternion.copy()
    
    # bake all frames
    if self.one_key_per_frame:
        for f in range(self.frame_start, self.frame_end +1):      
            bpy.context.scene.frame_set(f)   
            # set back original head lock state for this frame
            c_prop_bone[prop_name] = limb_lock_states[f]            
            c_limb_fk.rotation_euler, c_limb_fk.rotation_quaternion = limb_rots[f]
            update_transform()
            # snap
            _snap_limb_lock(self, add_keyframe=True)
    
    else:# bake only existing keyframes
        # collect frames that have keyframes
        ctrls = [c_limb_fk_name] if self.bone_type == 'arm' else [c_limb_fk_name, ard.leg_bones_dict['thigh']['control_fk']+self.side]      
        frames_idx = []
        
        for base_name in ctrls:
            fc_start_dp = 'pose.bones["'+base_name+'"].'

            for fc in get_action_fcurves(armature.animation_data.action):
                if fc.data_path.startswith(fc_start_dp):
                    for keyf in fc.keyframe_points:
                        if keyf.co[0] >= self.frame_start and keyf.co[0] <= self.frame_end:
                            if not keyf.co[0] in frames_idx:
                                frames_idx.append(keyf.co[0])
            
        for f in frames_idx:
            bpy.context.scene.frame_set(int(f))    
            # set back original head lock state for this frame
            c_prop_bone[prop_name] = limb_lock_states[f]
            c_limb_fk.rotation_euler, c_limb_fk.rotation_quaternion = limb_rots[f]
            update_transform()
            # snap                
            _snap_limb_lock(self, add_keyframe=True)

   
def _snap_limb_lock(self, add_keyframe=False):
    c_limb_fk_name = ard.arm_bones_dict['arm']['control_fk']+self.side if self.bone_type == 'arm' else ard.leg_bones_dict['upthigh']+self.side
    c_limb_fk = get_pose_bone(c_limb_fk_name)
    c_prop_bone_name = ard.arm_bones_dict['shoulder']['control']+self.side if self.bone_type == 'arm' else ard.leg_bones_dict['upthigh']+self.side
    c_prop_bone = get_pose_bone(c_prop_bone_name)
    prop_name = 'arm_lock' if self.bone_type == 'arm' else 'thigh_lock'
    
    # store current matrix
    mat = c_limb_fk.matrix.copy()
    
    # switch
    c_prop_bone[prop_name] = 1 if c_prop_bone[prop_name] == 0 else 0
    
    # Constraints support
    # disable constraints
    cns_states = []
    for cns in c_limb_fk.constraints:
        cns_states.append(cns.enabled)
        cns.enabled = False
        
    update_transform()
    
    # snap (no cns)
    c_limb_fk.matrix = mat
    update_transform()
    mat_no_cns = c_limb_fk.matrix.copy()
    
    # enable constraints
    for ci, cns in enumerate(c_limb_fk.constraints):
        cns.enabled = cns_states[ci]
    
    update_transform()
    
    # compensate constraints offset
    mat_cns = c_limb_fk.matrix.copy()
    mat_diff = mat_cns.inverted() @ mat_no_cns
    # snap
    c_limb_fk.matrix = mat_no_cns @ mat_diff
    
    update_transform()
    
    # ensure location remains zeroed out
    c_limb_fk.location = [0,0,0]
    
    #insert keyframe if autokey enable
    if bpy.context.scene.tool_settings.use_keyframe_insert_auto or add_keyframe:
        c_prop_bone.keyframe_insert(data_path='["'+prop_name+'"]')
        c_limb_fk.keyframe_insert(data_path="rotation_quaternion" if c_limb_fk.rotation_mode == 'QUATERNION' else 'rotation_euler')

   
def _bake_snap_head(self):
    armature = bpy.context.active_object
    head_ctrl_name = ard.heads_dict['control'][:-2]+self.side
    c_head_pb = get_pose_bone(head_ctrl_name)
    
    # store original head lock state for each frame
    head_lock_states = {}
    head_rots = {}
    
    for f in range(self.frame_start, self.frame_end +1):
        bpy.context.scene.frame_set(f)
        head_lock_states[f] = c_head_pb['head_free']
        head_rots[f] = c_head_pb.rotation_euler.copy(), c_head_pb.rotation_quaternion.copy()
    
    # bake all frames
    if self.one_key_per_frame:
        for f in range(self.frame_start, self.frame_end +1):      
            bpy.context.scene.frame_set(f)   
            # set back original head lock state for this frame
            c_head_pb['head_free'] = head_lock_states[f]            
            c_head_pb.rotation_euler, c_head_pb.rotation_quaternion = head_rots[f]
            update_transform()
            # snap
            _snap_head(self.side, add_keyframe=True)
    
    else:# bake only existing keyframes
        # collect frames that have keyframes
        head_ctrls = [head_ctrl_name]        
        frames_idx = []
        
        for base_name in head_ctrls:
            fc_start_dp = 'pose.bones["'+base_name+'"].'

            for fc in get_action_fcurves(armature.animation_data.action):
                if fc.data_path.startswith(fc_start_dp):
                    for keyf in fc.keyframe_points:
                        if keyf.co[0] >= self.frame_start and keyf.co[0] <= self.frame_end:
                            if not keyf.co[0] in frames_idx:
                                frames_idx.append(keyf.co[0])
        
        for f in frames_idx:
            bpy.context.scene.frame_set(int(f))    
            # set back original head lock state for this frame
            c_head_pb['head_free'] = head_lock_states[f]
            c_head_pb.rotation_euler, rotquat = head_rots[f]                
            update_transform()
            # snap                
            _snap_head(self.side, add_keyframe=True)
            

def _snap_head(side, add_keyframe=False):
    head_ctrl_name = ard.heads_dict['control'][:-2]+side
    c_head = get_pose_bone(head_ctrl_name)
    head_s_f_name = ard.heads_dict['scale_fix'][:-2]+side
    head_scale_fix = get_pose_bone(head_s_f_name)

    # get the bone parent (constrained) of head_scale_fix
    head_scale_fix_parent = None
    for cns in head_scale_fix.constraints:
        if cns.type == "CHILD_OF" and cns.influence == 1.0:
            head_scale_fix_parent = get_pose_bone(cns.subtarget)

    c_head_loc = c_head.location.copy()

    # matrices evaluations
    c_head_mat = c_head.matrix.copy()
    head_scale_fix_mat = head_scale_fix_parent.matrix_channel.inverted() @ head_scale_fix.matrix_channel

    # switch the prop
    c_head["head_free"] = 0 if c_head["head_free"] == 1 else 1

    # apply the matrices
    # two time because of a dependency lag
    for i in range(0,2):
        update_transform()
        c_head.matrix = head_scale_fix_mat.inverted() @ c_head_mat
        # the location if offset, preserve it
        c_head.location = c_head_loc

    #insert keyframe if autokey enable
    if bpy.context.scene.tool_settings.use_keyframe_insert_auto or add_keyframe:
        c_head.keyframe_insert(data_path='["head_free"]')
        c_head.keyframe_insert(data_path="rotation_quaternion" if c_head.rotation_mode == 'QUATERNION' else 'rotation_euler')
        
            
def _set_picker_camera(self):
    bpy.ops.object.mode_set(mode='OBJECT')

    #save current scene camera
    current_cam = bpy.context.scene.camera

    rig = bpy.data.objects.get(bpy.context.active_object.name)
    
    bpy.ops.object.select_all(action='DESELECT')
    
    cam_ui = None
    rig_ui = None
    ui_mesh = None
    char_name_text = None
    
    is_a_proxy = False
    if 'proxy_collection' in dir(rig):# proxy support
        if rig.proxy_collection:
            is_a_proxy = True
            children = rig.proxy_collection.instance_collection.all_objects
    if not is_a_proxy:
        children = rig.children

    for child in children:
        if child.type == 'CAMERA' and 'cam_ui' in child.name:
            cam_ui = child
        if child.type == 'EMPTY' and 'rig_ui' in child.name:
            rig_ui = child
            for _child in rig_ui.children:
                if _child.type == 'MESH' and 'mesh' in _child.name:
                    ui_mesh = _child

    # if the picker is not there, escape
    if rig_ui == None and is_proxy(rig) == False:
        self.report({'INFO'}, 'No picker found, click "Add Picker" to add one.')
        return

    # ui cam not found, add one
    active_obj_name = bpy.context.active_object.name
    if not cam_ui:
        bpy.ops.object.camera_add(align='VIEW', enter_editmode=False, location=(0, 0, 0), rotation=(0, 0, 0))
        # set cam data
        bpy.context.active_object.name = 'cam_ui'
        cam_ui = bpy.data.objects['cam_ui']
        cam_ui.data.type = 'ORTHO'
        cam_ui.data.display_size = 0.1
        cam_ui.data.show_limits = False
        cam_ui.data.show_passepartout = False
        cam_ui.parent = bpy.data.objects[active_obj_name]

        # set collections
        for col in bpy.data.objects[active_obj_name].users_collection:
            try:
                col.objects.link(cam_ui)
            except:
                pass

    set_active_object(active_obj_name)
    
    
    if cam_ui: 
    
        # isolate the rig and UI objects
        #   select UI objects
        for mesh_child in rig_ui.children:
            mesh_child.hide_select = False
            set_active_object(mesh_child.name)
       
        bpy.ops.view3d.localview()
        
        # set viewport cam
        space_data = bpy.context.space_data
        space_data.use_local_camera = True
        space_data.camera = cam_ui
        space_data.region_3d.view_perspective = 'CAMERA'

        # set viewport display options
        #bpy.context.space_data.lock_camera_and_layers = False
        space_data.overlay.show_relationship_lines = False
        space_data.overlay.show_text = False
        space_data.overlay.show_cursor = False
        current_area = bpy.context.area
        space_view3d = [i for i in current_area.spaces if i.type == 'VIEW_3D']
        space_view3d[0].shading.type = 'SOLID'
        space_view3d[0].shading.show_object_outline = False
        space_view3d[0].shading.show_specular_highlight = False
        space_view3d[0].show_gizmo_navigate = False
        space_view3d[0].use_local_camera = True
        bpy.context.space_data.lock_camera = False#unlock camera to view
        
        # Note on X-ray management
        # X-ray should be disabled to avoid UI mesh to be drawn on top of bone shapes...
        # but: shading.show_xray AND bpy.ops.view3d.toggle_xray() are different x-ray states,
        # it seems there's no API for the "Toggle X-Ray" button (header menu) in Pose mode (object and pose mode have different states)
        # and, object.show_in_front is a third x-ray state (!), but this is object level, not window level, so it affects non-picker windows...
        # Todo...?
        
        rig_ui_scale = 1.0

        if rig_ui:
            rig_ui_scale = rig_ui.scale[0]

        units_scale = bpy.context.scene.unit_settings.scale_length
        fac_ortho = 1.8# * (1/units_scale)

        # Position the camera height to the backplate height
        if ui_mesh:
            vert_pos = [v.co for v in ui_mesh.data.vertices]
            vert_pos = sorted(vert_pos, reverse=False, key=itemgetter(2))
            max1 = ui_mesh.matrix_world @ vert_pos[0]
            max2 = ui_mesh.matrix_world @ vert_pos[len(vert_pos)-1]
            picker_size = (max1-max2).magnitude
            picker_center = (max1+max2)/2
            
            # set the camera matrix            
            pos_Z_world = rig.matrix_world.inverted() @ Vector((0.0, 0.0, picker_center[2]))
            cam_ui.matrix_world = rig.matrix_world @ Matrix.Translation(Vector((0, -40, pos_Z_world[2])))
            
            cam_ui.scale = (1.0,1.0,1.0)
            cam_ui.rotation_euler = (radians(90), 0, 0)

            # set the camera clipping and ortho scale
            bpy.context.evaluated_depsgraph_get().update()
            dist = (cam_ui.matrix_world.to_translation() - picker_center).length
            cam_ui.data.clip_start = dist*0.9
            cam_ui.data.clip_end = dist*1.1
            cam_ui.data.ortho_scale = fac_ortho * picker_size

        #   make UI objects unselectable
        for mesh_child in rig_ui.children:
            mesh_child.hide_select = True

    else:
        self.report({'ERROR'}, 'No picker camera found for this rig')

    #back to pose mode
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(state=1)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='POSE')

    # enable the picker addon
    try:
        bpy.context.scene.Proxy_Picker.active = True
    except:
        pass


def convert_rot_mode(self):
    scn = bpy.context.scene
    armature = bpy.context.active_object
    rot_mode_tar = self.mode
    current_frame = scn.frame_current
    
    def set_target_rot_mode(pb):
        pb.rotation_mode = 'QUATERNION' if rot_mode_tar == 'rotation_quaternion' else self.euler_order
        
    def insert_keyframe(pb):
        pb.keyframe_insert(data_path=rot_mode_tar)
        # Todo, auto-keyframing the rot mode is not supported for now, it leads to rotation conversion update issue
        # see if it can be fixed later
        #if self.key_rot_mode:
        #    pb.keyframe_insert(data_path='rotation_mode')


    pose_bones = bpy.context.selected_pose_bones if self.selected_only else armature.pose.bones
    
    if len(pose_bones) == 0:
        return
        
    for pb in pose_bones:
        current_mode = pb.rotation_mode
        pb_path = pb.path_from_id() 
        fc_data_path = pb_path+'.rotation_quaternion' if current_mode == 'QUATERNION' else pb_path+'.rotation_euler'        
        fc = find_fcurve(armature.animation_data.action, fc_data_path)
        
        if fc == None and self.selected_only == False:# only animated bones, otherwise could insert keyframes on unwanted bones (rig mechanics)
            continue
                
        keyf_to_del = []
                
        if self.one_key_per_frame:            
                
            for f in range(self.frame_start, self.frame_end +1):
                scn.frame_set(f)
                
                for pb in pose_bones:
                    current_mode = pb.rotation_mode
                    
                    # convert rot mode
                    set_target_rot_mode(pb)                          
                    
                    # add keyframe
                    insert_keyframe(pb)
                    
                    # restore rot mode for next keyframe
                    if f != self.frame_end:
                        pb.rotation_mode = current_mode
        
        else:# only convert existing keyframes     
            if fc == None:
                # no keyframes yet, convert rot mode
                set_target_rot_mode(pb)
                continue                
            
            for keyf in fc.keyframe_points:
                if keyf.co[0] >= self.frame_start and keyf.co[0] <= self.frame_end:
                    scn.frame_set(int(keyf.co[0]))
                    keyf_to_del.append(keyf.co[0])
                    set_target_rot_mode(pb)
                    insert_keyframe(pb)
                    
                    # restore rot mode for next keyframe                    
                    pb.rotation_mode = current_mode                    
        
                        
        set_target_rot_mode(pb)
        
    # restore initial frame
    scn.frame_set(current_frame)
    

def _toggle_multi(limb, id, key):
    bone_list = []

    if limb == 'arm':
        bone_list = ard.arm_displayed + ard.fingers_displayed
    if limb == 'leg':
        bone_list = ard.leg_control

    if get_pose_bone('c_pos')[key] == 1:
        get_pose_bone('c_pos')[key] = 0
    else:
        get_pose_bone('c_pos')[key] = 1

    for bone in bone_list:
        current_bone = get_data_bone(bone+'_dupli_'+id)
        if current_bone:      
            if get_pose_bone('c_pos')[key] == 0:
                current_bone.hide = True
            else:
                current_bone.hide = False   



# Rig UI Panels ##################################################################################################################
class ArpRigToolsPanel:
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'    
    bl_category = "Tool"
    
    
class ARP_PT_RigProps(Panel, ArpRigToolsPanel):
    bl_label = "Rig Main Properties"    
    
    @classmethod
    def poll(self, context):
        if context.active_object:
            return context.active_object.type == "ARMATURE"      
        
        
    def draw(self, context): 
        pass    


class ARP_PT_RigProps_LayerSets(Panel, ArpRigToolsPanel):
    bl_label = "Rig Layers"
    bl_parent_id = "ARP_PT_RigProps"   
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        scn = bpy.context.scene
        rig = context.active_object        
       
        row = layout.row(align=True)
        row.template_list("ARP_UL_layers_sets_list", "", rig, "layers_sets", rig, "layers_sets_idx", rows=5)
        col = row.column(align=True)
        col.operator(ARP_OT_layers_sets_add.bl_idname, text="", icon="ADD")
        col.operator(ARP_OT_layers_sets_remove.bl_idname, text="", icon="REMOVE")
        col.separator()
        col.menu("ARP_MT_layers_sets_menu", icon='DOWNARROW_HLT', text="")
        col.separator()
        col.separator()
        col.operator(ARP_OT_layers_sets_move.bl_idname, text="", icon="TRIA_UP").direction = 'UP'
        col.operator(ARP_OT_layers_sets_move.bl_idname, text="", icon="TRIA_DOWN").direction = 'DOWN'
   
        layout.separator()
        
 
class ARP_PT_BoneCustomProps(Panel, ArpRigToolsPanel):
    bl_label = "Bone Properties"
    bl_parent_id = "ARP_PT_RigProps"   
    bl_options = {'DEFAULT_CLOSED'}
       
    @classmethod    
    def poll(self, context):
        return context.mode == 'POSE'
   
    def draw(self, context):
        try:
            active_bone = context.selected_pose_bones[0]
        except:
            return
        
        layout = self.layout  
        col = layout.column(align=True)   
        rig = bpy.context.active_object
            
        # pinned props
        if 'arp_pinned_props' in rig.data.keys():
            pinned_props_list = get_pinned_props_list(rig)
            
            if len(rig.data['arp_pinned_props']):
                col.label(text="Pinned Props:")
                
                for prop_dp in pinned_props_list:
                    if prop_dp == '':
                        continue
                    dp_pb = prop_dp.split('][')[0] + ']'
                    
                    dp_pb_resolved = rig.path_resolve(dp_pb)
                    prop_name = prop_dp.split(']["')[1][:-2]
                    row = col.row(align=True)
                    row.prop(dp_pb_resolved, '["'+prop_name+'"]')
                    btn = row.operator(ARP_OT_property_pin.bl_idname, text='', icon='PINNED')
                    btn.state = False
                    btn.prop = prop_name
                    btn.prop_dp_pb = dp_pb
                    
                col.separator()
                
        if len(active_bone.keys()):
            for prop_name in active_bone.keys():
                if prop_name.startswith('_RNA_'):
                    continue
                row = col.row(align=True)
                row.prop(active_bone, '["'+prop_name+'"]')
                btn = row.operator(ARP_OT_property_pin.bl_idname, text='', icon='UNPINNED')
                btn.state = True
                btn.prop = prop_name
        

class ARP_PT_RigProps_Settings(Panel, ArpRigToolsPanel):
    bl_label = "Settings"
    bl_parent_id = "ARP_PT_RigProps"

    @classmethod
    def poll(self, context):
        return context.mode == 'POSE'
        
    
    def draw(self, context):
        layout = self.layout
        scn = bpy.context.scene
        rig = context.active_object
        
        active_bone = None
        selected_bone_name = None
        try:
            active_bone = context.selected_pose_bones[0]#context.active_pose_bone
            selected_bone_name = active_bone.name
        except:
            pass
            
        if active_bone and selected_bone_name:
            if context.active_object.data.get("rig_id") != None:# Auto-Rig Pro armatures settings only
                # Get bone side
                bone_side = get_bone_side(selected_bone_name)
                
                # Spine
                if is_selected(spines_ctrls, selected_bone_name, startswith=True):
                    c_root_master_pb = get_pose_bone('c_root_master'+bone_side)

                    if c_root_master_pb:
                        col = layout.column(align=True)
                        if 'spine_stretch_volume' in c_root_master_pb.keys():                        
                            col.prop(c_root_master_pb, '["spine_stretch_volume"]', text='Spine Stretch')
                        if 'reverse_spine' in c_root_master_pb.keys():
                            col.separator()
                            col.operator(ARP_OT_snap_reversed_spine.bl_idname, text='Snap Fwd-Rev Spine')
                            col.prop(c_root_master_pb, '["reverse_spine"]', text='Reverse Switch')
                    
                    
                # Leg
                if (is_selected(fk_leg, selected_bone_name) or is_selected(ik_leg, selected_bone_name)):
                    
                    c_foot_ik = get_pose_bone(ik_leg[2]+bone_side)
                    c_foot_fk = get_pose_bone(fk_leg[2]+bone_side)
                    
                    # IK-FK Switch
                    col = layout.column(align=True)
                    row = col.row(align=True)
                    row.operator(ARP_OT_switch_snap.bl_idname, text="Snap IK-FK")

                    row.prop(scn, "show_ik_fk_advanced", text="", icon="SETTINGS")
                    col.prop(c_foot_ik, '["ik_fk_switch"]', text="IK-FK Switch", slider=True)

                    if scn.show_ik_fk_advanced:
                        col.operator("pose.arp_leg_fk_to_ik_", text="Snap IK > FK (Leg)")
                        col.operator("pose.arp_leg_ik_to_fk_", text="Snap FK > IK (Leg)")
                        col.operator("pose.arp_bake_leg_fk_to_ik", text="Bake IK > FK (Leg)...")
                        col.operator("pose.arp_bake_leg_ik_to_fk", text="Bake FK > IK (Leg)...")
                        if 'pole_viz' in c_foot_ik.keys():
                            col.prop(c_foot_ik, '["pole_viz"]' , text="Show IK Pole Line")
                        
                    layout.separator() 
                    
                    c_thighb = get_pose_bone("c_thigh_b"+bone_side)
                    
                    if is_selected(fk_leg, selected_bone_name):
                        # FK Lock property               
                        if 'thigh_lock' in c_thighb.keys():
                            col = layout.column(align=True)
                            row = col.row(align=True)
                            row.operator(ARP_OT_snap_limb_lock.bl_idname, text='Snap Thigh Lock')
                            row.prop(scn, 'show_limb_lock_advanced', text='', icon="SETTINGS")
                            col.prop(c_thighb, '["thigh_lock"]', text="Leg Lock", slider=True)
                            if scn.show_limb_lock_advanced:
                                col.operator(ARP_OT_bake_limb_lock.bl_idname, text='Bake Thigh Lock...')
                            
                        # Stretch length property
                        layout.prop(c_foot_fk, '["stretch_length"]', text="Stretch Length (FK)", slider=True)
                        
                    if is_selected(ik_leg, selected_bone_name):   
                        col = layout.column(align=True)
                        col.prop(c_foot_ik, '["stretch_length"]', text="Stretch Length (IK)", slider=True)                
                        col.prop(c_foot_ik, '["auto_stretch"]', text="Auto Stretch", slider=True)
                        
                        # 3 bones IK
                        if "three_bones_ik" in c_foot_ik.keys():                        
                            layout.prop(c_foot_ik, '["three_bones_ik"]' , text="3 Bones IK", slider=True)
                        elif 'three_bones_ik_type2' in c_foot_ik.keys():
                            col = layout.column(align=True)
                            col.prop(c_foot_ik, '["leg_lock_z"]' , text="IK Calf Lock")
                            col.prop(c_foot_ik, '["stiffness_calf"]' , text="IK Calf Stiffness")
                            col.prop(c_foot_ik, '["stiffness_thigh_b"]' , text="IK ThighB Stiffness")
                            
                            
                    # Twist tweak            
                    if "thigh_twist" in c_thighb.keys():# backward-compatibility
                        layout.prop(c_thighb, '["thigh_twist"]', text="Thigh Twist", slider=True)
                    
                    # Fix_roll prop
                    layout.prop(c_foot_ik, '["fix_roll"]', text="Fix Roll", slider=True)            


                    if is_selected(ik_leg, selected_bone_name):
                        # IK Pole parent
                        if "pole_parent" in get_pose_bone("c_leg_pole" + bone_side).keys():
                            col = layout.column(align=True)
                            row = col.row(align=True)                                            
                            row.operator("pose.arp_snap_pole", text = "Snap Pole Parent")
                            row.prop(scn, 'show_snap_pole_advanced', text='', icon='SETTINGS')
                            str = ''
                            if get_pose_bone('c_leg_pole'+bone_side)['pole_parent'] == 0:
                                str = 'Global'
                            elif get_pose_bone('c_leg_pole'+bone_side)['pole_parent'] == 1:
                                str = 'Foot'
                            elif get_pose_bone('c_leg_pole'+bone_side)['pole_parent'] == 2:
                                str = 'Smart'
                            col.prop(get_pose_bone('c_leg_pole'+bone_side), '["pole_parent"]', text='Pole Parent: '+str, slider=True)
                            if scn.show_snap_pole_advanced:
                                col.operator(ARP_OT_bake_pole.bl_idname, text="Bake Pole Parent...")
                                
                        # foot roll break
                        if 'roll_break_point' in c_foot_ik.keys():                        
                            col = layout.column(align=True)
                            row = col.row(align=True)
                            row.prop(c_foot_ik, '["roll_break_point"]', text='Foot Roll Break Point')
                            row.prop(scn, 'show_footroll_advanced', text='', icon='SETTINGS')
                        if scn.show_footroll_advanced:
                            if 'roll_speed' in c_foot_ik.keys():
                                col.prop(c_foot_ik, '["roll_speed"]', text='Foot Roll Speed')
                            if 'roll_break_overshoot' in c_foot_ik.keys():
                                col.prop(c_foot_ik, '["roll_break_overshoot"]', text='Foot Roll Overshoot')
                            if 'roll_break_unfold_speed' in c_foot_ik.keys():
                                col.prop(c_foot_ik, '["roll_break_unfold_speed"]', text='Foot Roll Unfold Lag')
                            

                    # Pin Snap
                    layout.separator()
                    col = layout.column(align=True)
                    p = col.operator("pose.arp_snap_pin", text="Snap Pinning")
                    # Pinning
                    col.prop(get_pose_bone("c_stretch_leg"+ bone_side), '["leg_pin"]', text="Knee Pinning", slider=True)

                
                # Toes
                if is_selected(toes_start, selected_bone_name, startswith=True):
                    toe_type = None
                    for type in fingers_type_list:
                        if type in selected_bone_name:
                            toe_type = type
                            break

                    layout.label(text="Toes "+toe_type.title()+" "+bone_side+":")

                    toes_root = get_pose_bone("c_toes_"+toe_type+"1_base"+bone_side)

                    # Toes IK-FK
                    if toes_root and 'ik_fk_switch' in toes_root.keys():
                        # IK FK Switch
                        col = layout.column(align=True)
                        row = col.row(align=True).split(factor=0.8, align=True)
                        op = row.operator(ARP_OT_switch_snap.bl_idname, text='Snap IK-FK')
                        op.all = False
                        op.finger_root_name = toes_root.name                
                        
                        op_all = row.operator(ARP_OT_switch_snap.bl_idname, text='All')
                        op_all.all = True
                        op_all.finger_root_name = toes_root.name
                        op_all.toe_type = toe_type
                        
                        row = col.row(align=True).split(factor=0.8, align=True)
                        row.prop(toes_root, '["ik_fk_switch"]', text='IK-FK', slider=True)
                        but = row.operator('pose.arp_toes_set_all', text='All')
                        but.prop_name = 'ik_fk_switch'
                        but.root_name = toes_root.name
                        but.toe_type = toe_type
                        
                        # Invert IK Direction
                        col = layout.column(align=True)                
                        row = col.row(align=True).split(factor=0.8, align=True)
                        row.prop(toes_root, '["ik_invert_dir"]', text='Invert IK Dir')
                        but = row.operator('pose.arp_toes_set_all', text='All')
                        but.prop_name = 'ik_invert_dir'
                        but.root_name = toes_root.name
                        but.toe_type = toe_type
                        
                        row = col.row(align=True).split(factor=0.8, align=True)
                        row.prop(toes_root, '["ik_invert_dir_offset"]', text='Offset')
                        but = row.operator('pose.arp_toes_set_all', text='All')
                        but.prop_name = 'ik_invert_dir_offset'
                        but.root_name = toes_root.name
                        but.toe_type = toe_type
                        
                        # Show IK Pole
                        col = layout.column()                
                        row = col.row(align=True).split(factor=0.8, align=True)
                        row.prop(toes_root, '["show_ik_pole"]', text='Show Pole')
                        but = row.operator('pose.arp_toes_set_all', text='All')
                        but.prop_name = 'show_ik_pole'
                        but.root_name = toes_root.name
                        but.toe_type = toe_type
                        
                        # Snape All to IK/FK
                        row = col.row(align=True).split(factor=0.7, align=True)
                        btn = row.operator(ARP_OT_switch_all_fingers.bl_idname, text='Snap All to IK')
                        btn.state = 'IK'
                        btn.side = bone_side
                        btn = row.operator(ARP_OT_switch_all_fingers.bl_idname, text='FK')
                        btn.state = 'FK'
                        btn.side = bone_side
                        
                
                # Arm
                if is_selected(fk_arm, selected_bone_name) or is_selected(ik_arm, selected_bone_name):
                
                    # IK-FK Switch
                    col = layout.column(align=True)
                    row = col.row(align=True)
                    row.operator(ARP_OT_switch_snap.bl_idname, text="Snap IK-FK")

                    row.prop(scn, "show_ik_fk_advanced", text="", icon="SETTINGS")
                    col.prop(get_pose_bone("c_hand_ik" + bone_side), '["ik_fk_switch"]', text="IK-FK Switch", slider=True)

                    if scn.show_ik_fk_advanced:
                        col.operator("pose.arp_arm_fk_to_ik_", text="Snap IK > FK (Arm)")
                        col.operator("pose.arp_arm_ik_to_fk_", text="Snap FK > IK (Arm)")
                        col.operator("pose.arp_bake_arm_fk_to_ik", text="Bake IK > FK (Arm)...")
                        col.operator("pose.arp_bake_arm_ik_to_fk", text="Bake FK > IK (Arm)...")
                    
                    layout.separator() 
                    
                    if is_selected(fk_arm, selected_bone_name):
                        # FK Lock property
                        c_shoulder = get_pose_bone("c_shoulder" + bone_side)
                        if 'arm_lock' in c_shoulder.keys():
                            col = layout.column(align=True)
                            row = col.row(align=True)
                            row.operator(ARP_OT_snap_limb_lock.bl_idname, text='Snap Arm Lock')
                            row.prop(scn, 'show_limb_lock_advanced', text='', icon="SETTINGS")
                            col.prop(c_shoulder, '["arm_lock"]', text="Arm Lock", slider=True)
                            if scn.show_limb_lock_advanced:
                                col.operator(ARP_OT_bake_limb_lock.bl_idname, text='Bake Arm Lock...')
                                
                        # stretch length property
                        layout.prop(get_pose_bone("c_hand_fk" + bone_side), '["stretch_length"]', text="Stretch Length (FK)", slider=True)
                        
                    if is_selected(ik_arm, selected_bone_name):
                        if 'pole_viz' in get_pose_bone("c_hand_ik" + bone_side).keys():
                            layout.prop(get_pose_bone("c_hand_ik" + bone_side), '["pole_viz"]' , text="Show IK Pole Line")
                        layout.prop(get_pose_bone("c_hand_ik" + bone_side), '["stretch_length"]', text="Stretch Length (IK)", slider=True)
                        # Auto_stretch ik
                        layout.prop(get_pose_bone("c_hand_ik" + bone_side), '["auto_stretch"]', text="Auto Stretch", slider=True)
                        
                    # Twist tweak
                    c_shoulder = get_pose_bone("c_shoulder"+bone_side)
                    if "arm_twist" in c_shoulder.keys():# backward-compatibility
                        layout.prop(c_shoulder, '["arm_twist"]', text="Arm Twist", slider=True)


                    if is_selected(ik_arm, selected_bone_name):
                        # IK Pole parent
                        if "pole_parent" in get_pose_bone('c_arms_pole'+bone_side).keys():
                            col = layout.column(align=True)
                            row = col.row(align=True)
                            row.operator("pose.arp_snap_pole", text = "Snap Pole Parent")
                            row.prop(scn, 'show_snap_pole_advanced', text='', icon='SETTINGS')
                            
                            str = ''
                            if get_pose_bone('c_arms_pole'+bone_side)['pole_parent'] == 0:
                                str = 'Global'
                            elif get_pose_bone('c_arms_pole'+bone_side)['pole_parent'] == 1:
                                str = 'Local'                        
                            col.prop(get_pose_bone("c_arms_pole" + bone_side), '["pole_parent"]', text='Pole Parent: '+str, slider=True)
                            
                            if scn.show_snap_pole_advanced:
                                col.operator(ARP_OT_bake_pole.bl_idname, text='Bake Pole Parent...')

                    # Pin Snap
                    layout.separator()
                    col = layout.column(align=True)
                    col.operator("pose.arp_snap_pin", text="Snap Pinning")
                    # Pinning
                    col.prop(get_pose_bone("c_stretch_arm"+ bone_side), '["elbow_pin"]', text="Elbow Pinning", slider=True)

                # Eye Aim
                if is_selected(eye_aim_bones, selected_bone_name):
                    layout.prop(get_pose_bone("c_eye_target" + bone_side[:-2] + '.x'), '["eye_target"]', text="Eye Target", slider=True)


                # Auto-eyelid
                for eyel in auto_eyelids_bones:
                    if is_selected(eyel+bone_side, selected_bone_name):
                        eyeb = get_pose_bone('c_eye'+bone_side)                        
                        if len(eyeb.keys()):
                            col = layout.column(align=True)
                            if 'auto_eyelid' in eyeb.keys():# backward-compatibility
                                col.separator()
                                col.prop(get_pose_bone('c_eye'+bone_side), '["auto_eyelid"]', text='Auto-Eyelid', slider=True)
                            if 'auto_eyelid_top' in eyeb.keys():# backward-compatibility
                                col.prop(get_pose_bone('c_eye'+bone_side), '["auto_eyelid_top"]', text='Upper Eyelid', slider=True)
                            if 'auto_eyelid_bot' in eyeb.keys():# backward-compatibility
                                col.prop(get_pose_bone('c_eye'+bone_side), '["auto_eyelid_bot"]', text='Lower Eyelid', slider=True)


                # Fingers
                if is_selected(fingers_start, selected_bone_name, startswith=True):
                    finger_type = None
                    for type in fingers_type_list:
                        if type in selected_bone_name:
                            finger_type = type
                            break

                    layout.label(text=finger_type.title()+" "+bone_side+":")

                    finger_root = get_pose_bone("c_"+finger_type+"1_base"+bone_side)

                    # Fingers IK-FK switch
                    if 'ik_fk_switch' in finger_root.keys():
                        col = layout.column(align=True)
                        col.operator(ARP_OT_switch_snap.bl_idname, text='Snap IK-FK')
                        col.prop(finger_root, '["ik_fk_switch"]', text='IK-FK', slider=True)
                        row = col.row(align=True).split(factor=0.7, align=True)
                        
                        btn = row.operator(ARP_OT_switch_all_fingers.bl_idname, text='Snap All to IK')
                        btn.state = 'IK'
                        btn.side = bone_side
                        btn = row.operator(ARP_OT_switch_all_fingers.bl_idname, text='FK')
                        btn.state = 'FK'
                        btn.side = bone_side

                        if 'ik_tip' in finger_root.keys():# backward-compatibility
                            col = layout.column(align=True)                    
                            col.operator(ARP_OT_switch_snap_root_tip.bl_idname, text='Snap Root-Tip')
                            col.prop(finger_root, '["ik_tip"]', text='IK Root-Tip', slider=True)
                            row = col.row(align=True).split(factor=0.7, align=True)
                            btn = row.operator(ARP_OT_switch_snap_root_tip_all.bl_idname, text='Snap All to Root')
                            btn.state = 'ROOT'
                            btn.side = bone_side
                            btn = row.operator(ARP_OT_switch_snap_root_tip_all.bl_idname, text='Tip')
                            btn.state = 'TIP'
                            btn.side = bone_side

                        col.separator()

                        col.operator(ARP_OT_free_parent_ik_fingers.bl_idname, text='Toggle All IK Parents').side = bone_side

                        layout.separator()

                    # Fingers Bend
                    layout.prop(finger_root, '["bend_all"]', text='Bend All Phalanges', slider=True)


                # Fingers Grasp
                if is_selected(hands_ctrl, selected_bone_name):
                    if 'fingers_grasp' in get_pose_bone('c_hand_fk'+bone_side).keys():#if property exists, retro-compatibility check
                        layout.label(text='Fingers:')
                        layout.prop(get_pose_bone("c_hand_fk" + bone_side),  '["fingers_grasp"]', text = "Fingers Grasp", slider = False)


                # Pinning
                pin_arms = ["c_stretch_arm_pin", "c_stretch_arm_pin", "c_stretch_arm", "c_stretch_arm"]
                if is_selected(pin_arms, selected_bone_name):
                    if (selected_bone_name[-2:] == ".l"):
                        layout.label(text="Left Elbow Pinning")
                        layout.prop(get_pose_bone("c_stretch_arm"+ bone_side), '["elbow_pin"]', text="Elbow pinning", slider=True)
                    if (selected_bone_name[-2:] == ".r"):
                        layout.label(text="Right Elbow Pinning")
                        layout.prop(get_pose_bone("c_stretch_arm"+bone_side), '["elbow_pin"]', text="Elbow pinning", slider=True)

                pin_legs = ["c_stretch_leg_pin", "c_stretch_leg_pin", "c_stretch_leg", "c_stretch_leg"]


                if is_selected(pin_legs, selected_bone_name):
                    if selected_bone_name.endswith('.l'):
                        layout.label(text='Left Knee Pinning')
                        layout.prop(get_pose_bone('c_stretch_leg'+bone_side), '["leg_pin"]', text="Knee pinning", slider=True)
                    if selected_bone_name.endswith('.r'):
                        layout.label(text='Right Knee Pinning')
                        layout.prop(get_pose_bone('c_stretch_leg'+bone_side), '["leg_pin"]', text="Knee pinning", slider=True)


                # Head Lock
                if is_selected('c_head' + bone_side, selected_bone_name):
                    head_pbone = get_pose_bone('c_head' + bone_side)
                    if len(head_pbone.keys()) > 0:
                        if 'head_free' in head_pbone.keys():#retro compatibility
                            col = layout.column(align=True)
                            row = col.row(align=True)
                            op = row.operator(ARP_OT_snap_head.bl_idname, text="Snap Head Lock")
                            row.prop(scn, "show_head_lock_advanced", text='', icon="SETTINGS") 
                            col.prop(context.selected_pose_bones[0], '["head_free"]', text = 'Head Lock', slider = True)
                            
                            if scn.show_head_lock_advanced:
                                col.operator(ARP_OT_snap_head_bake.bl_idname, text='Bake Head Lock...')
                                
                    neck_pbone = get_pose_bone("c_neck"+bone_side)
                    if len(neck_pbone.keys()) > 0:
                        if "neck_global_twist" in neck_pbone.keys():
                            col = layout.column(align=True)
                            col.prop(neck_pbone, '["neck_global_twist"]', text = 'Neck Global Twist', slider = False)

                # Neck
                if selected_bone_name.startswith("c_neck") or selected_bone_name.startswith("c_subneck_"):
                    if len(active_bone.keys()):
                        if "neck_twist" in active_bone.keys():
                            col = layout.column(align=True)
                            neck_pbone = get_pose_bone("c_neck"+bone_side)
                            if len(neck_pbone.keys()):
                                if "neck_global_twist" in neck_pbone.keys():
                                    col = layout.column(align=True)
                                    col.prop(neck_pbone, '["neck_global_twist"]', text = 'Neck Global Twist', slider = False)

                            col.prop(active_bone, '["neck_twist"]', text = 'Neck Twist', slider = False)


                # Eyebrow mid
                if is_selected('c_eyebrow_mid'+bone_side, selected_bone_name):
                    if len(get_pose_bone('c_eyebrow_mid'+bone_side).keys()):
                        if 'eyeb_mid_soft' in get_pose_bone('c_eyebrow_mid'+bone_side).keys():
                            layout.prop(get_pose_bone('c_eyebrow_mid'+bone_side), '["eyeb_mid_soft"]', text='Eyebrow Mid Follow', slider=True)
                        
                # Lips Retain
                if is_selected('c_jawbone'+bone_side, selected_bone_name):
                    if len(get_pose_bone('c_jawbone'+bone_side).keys()):
                        if 'lips_retain' in get_pose_bone('c_jawbone'+bone_side).keys():
                            layout.prop(get_pose_bone("c_jawbone"+bone_side), '["lips_retain"]', text='Lips Retain', slider=True)
                            layout.prop(get_pose_bone("c_jawbone"+bone_side), '["lips_stretch"]', text='Lips Stretch', slider=True)
                        if 'lips_sticky_follow' in get_pose_bone('c_jawbone'+bone_side).keys():
                            layout.prop(get_pose_bone("c_jawbone"+bone_side), '["lips_sticky_follow"]', text='Lips Follow', slider=True)
                            
                # Soft Cheeks
                if is_selected('c_cheek_inflate'+bone_side, selected_bone_name):
                    if len(get_pose_bone('c_cheek_inflate'+bone_side).keys()):
                        col = layout.column(align=True)
                        if 'cheek_soft' in get_pose_bone('c_cheek_inflate'+bone_side).keys():
                            col.prop(get_pose_bone("c_cheek_inflate"+bone_side), '["cheek_soft"]', text='Soft Cheeks Amount', slider=True)                        
                        if 'cheek_lift' in get_pose_bone('c_cheek_inflate'+bone_side).keys():
                            col.prop(get_pose_bone("c_cheek_inflate"+bone_side), '["cheek_lift"]', text='Cheek Lift', slider=True)                    
                        if 'cheek_bulge' in get_pose_bone('c_cheek_inflate'+bone_side).keys():
                            col.prop(get_pose_bone("c_cheek_inflate"+bone_side), '["cheek_bulge"]', text='Cheek Bulge')
                        if 'cheek_pole' in get_pose_bone('c_cheek_inflate'+bone_side).keys():
                            col.prop(get_pose_bone("c_cheek_inflate"+bone_side), '["cheek_pole"]', text='Cheek Pole', slider=True)
                        

                # Spline IK
                if is_selected('c_spline_', selected_bone_name, startswith=True) or is_selected_prop(active_bone, 'arp_spline'):
                
                    layout.label(text='Spline IK')
                    spline_name = selected_bone_name.split('_')[1]
                    if active_bone.bone.keys() and 'arp_spline' in active_bone.bone.keys():
                        spline_name = active_bone.bone['arp_spline']

                    spline_root = get_pose_bone('c_'+spline_name+'_root'+bone_side)

                    if spline_root:
                        if 'ik_fk_switch' in spline_root.keys():
                            col = layout.column(align=True)
                            row = col.row(align=True)
                            op = row.operator('pose.arp_switch_snap', text='Snap IK-FK')
                            op.spline_name = spline_name
                            row.prop(scn, "show_ik_fk_advanced", text="", icon="SETTINGS")
                            col.prop(spline_root, '["ik_fk_switch"]', text='IK-FK Switch', slider=True)
                            
                            if scn.show_ik_fk_advanced:
                                op = col.operator(ARP_OT_spline_bake_fk_to_ik.bl_idname, text='Bake IK to FK (Spline)')
                                op.spline_name = spline_name
                                op = col.operator(ARP_OT_spline_bake_ik_to_fk.bl_idname, text='Bake FK to IK (Spline)')
                                op.spline_name = spline_name                                               
                                col.prop(scn, 'arp_spline_snap_precision', text='Precision')
                                col.prop(scn, 'arp_spline_snap_iter_max', text='Max Iterations')
                                col.prop(scn, 'arp_spline_snap_indiv', text='Snap All IK Controllers')
                                
                    if len(active_bone.keys()):
                        if 'twist' in active_bone.keys():
                            layout.prop(active_bone, '["twist"]', text="Twist")
                            
                    if spline_root:
                        
                        str = 'None'
                        if spline_root["y_scale"] == 1:
                            str = "Fit Curve"
                        elif spline_root["y_scale"] == 2:
                            str = "Bone Original"
                        layout.label(text="Y Scale:")
                        layout.prop(spline_root, '["y_scale"]', text = str)

                        str = "None"
                        if spline_root["stretch_mode"] == 1:
                            str = "Bone Original"
                        elif spline_root["stretch_mode"] == 2:
                            str = "Inverse Scale"
                        elif spline_root["stretch_mode"] == 3:
                            str = "Volume Preservation"
                        layout.label(text="XZ Scale:")
                        layout.prop(spline_root, '["stretch_mode"]', text=str)

                        layout.prop(spline_root, '["volume_variation"]', text = 'Volume Variation')
                        
                        if 'twist' in spline_root.keys():
                            layout.prop(spline_root, '["twist"]', text = 'Global Twist', slider=True)

                # Kilt
                if is_selected_prop(active_bone, 'arp_kilt'):
                    if 'kilt_name' in active_bone.bone.keys(): 
                        kilt_name = active_bone.bone['kilt_name']
                        
                        _s = '.x'
                        if 'kilt_type_side' in active_bone.bone.keys():
                            _s = '.x' if active_bone.bone['kilt_type_side'] == 'SYMMETRICAL' else active_bone.bone['kilt_type_side']
                            
                        kilt_master = get_pose_bone('c_'+kilt_name+'_master'+bone_side[:-2]+_s)
                        
                        if kilt_master:
                            layout.label(text="Kilt")           
                            layout.prop(kilt_master, '["collide"]', text='Collide')
                            layout.prop(kilt_master, '["collide_dist"]', text='Collide Distance')
                            layout.prop(kilt_master, '["collide_dist_falloff"]', text='Collide Falloff')
                            layout.prop(kilt_master, '["collide_spread"]', text='Collide Spread')
                
                
                # c_traj
                if is_selected('c_traj', selected_bone_name):
                    row = layout.column().row(align=True)
                    row.operator('arp.extract_root_motion', text='Extract Root Motion', icon='ANIM')
                    row.operator('arp.clear_root_motion', text='', icon='X')
            
            
            # All armatures settings
            # Child Of switcher        
            col = layout.column(align=True)
            col.separator()
            row = col.row(align=True)
            row.operator('arp.childof_switcher', text="Snap Child Of...", icon='CON_CHILDOF')        
            row.operator('arp.childof_keyer', text="", icon='KEY_HLT')
            
            if context.active_object.data.get("rig_id") != None:# Auto-Rig Pro armatures settings only
                # Multi Limb display
                if is_selected('c_pos', selected_bone_name):
                    layout.label(text='Multi-Limb Display:')
                    #look for multi limbs

                    if len(get_pose_bone('c_pos').keys()) > 0:
                        for key in get_pose_bone('c_pos').keys():

                            if 'leg' in key or 'arm' in key:
                                row = layout.column(align=True)
                                b = row.operator('id.toggle_multi', text=key)
                                if 'leg' in key:
                                    b.limb = 'leg'
                                if 'arm' in key:
                                    b.limb = 'arm'
                                b.id = key[-5:]
                                b.key = key
                                row.prop(get_pose_bone('c_pos'), '["'+key+'"]', text=key)

                    else:
                        layout.label(text='No Multiple Limbs')     
            
        
        if context.active_object.data.get("rig_id") != None:# Auto-Rig Pro armatures settings only, selection independent
            # Reset
            layout.separator()
            col = layout.column(align=True)
            col.operator(ARP_OT_reset_script.bl_idname, text="Reset All Pose")


class ARP_PT_RigProps_SetPickerCam(Panel, ArpRigToolsPanel):
    bl_label = "Picker"
    bl_parent_id = "ARP_PT_RigProps"   
    bl_options = {'DEFAULT_CLOSED'}
    
    @classmethod
    def poll(self, context):
        if context.mode != 'POSE':
            return False
        else:
            if context.active_object.data.get("rig_id") != None:
                return True
    
    def draw(self, context):
        layout = self.layout    
        col = layout.column(align=True)
        col.operator(ARP_OT_set_picker_camera_func.bl_idname, text="Set Picker Cam")#, icon = 'CAMERA_DATA')
        
        
class ARP_PT_RigProps_Utils(Panel, ArpRigToolsPanel):
    bl_label = "Rotation Mode Convertor"
    bl_parent_id = "ARP_PT_RigProps"   
    bl_options = {'DEFAULT_CLOSED'}
       
    @classmethod    
    def poll(self, context):
        return context.mode == 'POSE'
   
    def draw(self, context):
        layout = self.layout   
        col = layout.column(align=True)
        row = col.row(align=True)
        row.operator(ARP_OT_rotation_mode_convert.bl_idname, text="To Quaternions").mode = "rotation_quaternion"
        row.operator(ARP_OT_rotation_mode_convert.bl_idname, text="To Euler").mode = "rotation_euler"
        
           

###########  REGISTER  ##################
classes = (ARP_PT_RigProps, ARP_PT_RigProps_LayerSets, ARP_PT_BoneCustomProps, ARP_PT_RigProps_Settings, ARP_PT_RigProps_SetPickerCam,
        ARP_PT_RigProps_Utils, ARP_OT_snap_head, ARP_OT_snap_head_bake, ARP_OT_set_picker_camera_func, ARP_OT_toggle_multi, ARP_OT_snap_pole, ARP_OT_bake_pole,
        ARP_OT_arm_bake_fk_to_ik, ARP_OT_arm_fk_to_ik, ARP_OT_arm_bake_ik_to_fk, ARP_OT_arm_ik_to_fk, ARP_OT_switch_snap, 
        ARP_OT_leg_fk_to_ik, ARP_OT_leg_bake_fk_to_ik,  ARP_OT_leg_ik_to_fk, ARP_OT_leg_bake_ik_to_fk, ARP_OT_snap_pin, ARP_OT_snap_limb_lock, ARP_OT_bake_limb_lock,
        ARP_OT_toes_set_all,
        ARP_OT_reset_script, ARP_OT_free_parent_ik_fingers, ARP_OT_switch_all_fingers, ARP_OT_switch_snap_root_tip_all, ARP_OT_switch_snap_root_tip,
        ARP_UL_layers_sets_list, BoneCollectionSet, ObjectSet, LayerSet, 
        ARP_OT_layers_sets_add, ARP_OT_layers_sets_remove, ARP_OT_layers_sets_move, ARP_MT_layers_sets_menu, ARP_MT_layers_sets_menu_import, 
        ARP_MT_layers_sets_menu_export, ARP_OT_layers_set_import, ARP_OT_layers_set_import_preset, ARP_OT_layers_set_export, ARP_OT_layers_set_export_preset, 
        ARP_OT_layers_sets_all_toggle, ARP_OT_layers_add_defaults, ARP_PT_layers_sets_edit, ARP_OT_layers_sets_add_object, 
        ARP_OT_layers_sets_add_collection, ARP_OT_layers_sets_remove_collection,
        ARP_OT_layers_sets_clear_objects, ARP_OT_layers_sets_add_bones, ARP_OT_layers_sets_remove_bones, 
        ARP_OT_rotation_mode_convert, ARP_OT_property_pin, ARP_OT_childof_switcher, ARP_OT_childof_keyer,
        ARP_OT_snap_reversed_spine, ARP_OT_spline_bake_fk_to_ik, ARP_OT_spline_bake_ik_to_fk,
        ARP_OT_extract_root_motion, ARP_OT_clear_root_motion)


def update_arp_tab():
    interface_classes = (ARP_PT_RigProps, ARP_PT_RigProps_LayerSets, ARP_PT_BoneCustomProps, ARP_PT_RigProps_Settings, ARP_PT_RigProps_SetPickerCam, ARP_PT_RigProps_Utils)
    for cl in interface_classes:
        try:
            bpy.utils.unregister_class(cl)     
        except:
            pass
        
    ArpRigToolsPanel.bl_category = get_prefs().arp_tools_tab_name
    
    for cl in interface_classes:       
        bpy.utils.register_class(cl)
        
        
def update_layers_set_presets():
    presets_directory = get_prefs().rig_layers_path
    
    if not (presets_directory.endswith("\\") or presets_directory.endswith('/')):
        presets_directory += '/'

    try:
        os.listdir(presets_directory)
    except:
        return
    
    for file in os.listdir(presets_directory):
        if not file.endswith(".py"):
            continue
            
        preset_name = file.replace('.py', '')
        
        if preset_name in ARP_MT_layers_sets_menu_import.custom_presets:
            continue

        ARP_MT_layers_sets_menu_import.custom_presets.append(preset_name)


def register():
    from bpy.utils import register_class

    for cls in classes:    
        try:
            register_class(cls)
        except:
            pass
            

    update_arp_tab()
    update_layers_set_presets()
    
    bpy.app.handlers.frame_change_post.append(rig_layers_anim_update)
    
    if bpy.app.version >= (2,90,0):
        bpy.types.Object.layers_sets = CollectionProperty(type=LayerSet, name="Layers Set", description="List of bones layers set", override=get_override_dict_compat())
        bpy.types.Object.layers_sets_idx = IntProperty(name="List Index", description="Index of the layers set list", default=0, override={'LIBRARY_OVERRIDABLE'})
    else:# no overrides before 290
        bpy.types.Object.layers_sets = CollectionProperty(type=LayerSet, name="Layers Set", description="List of bones layers set")
        bpy.types.Object.layers_sets_idx = IntProperty(name="List Index", description="Index of the layers set list", default=0)
        
    bpy.types.Scene.show_ik_fk_advanced = BoolProperty(name="Show IK-FK operators", description="Show IK-FK advanced settings...", default=False)
    bpy.types.Scene.show_limb_lock_advanced = BoolProperty(name="Arm/Leg Lock Advanced Operators", description="Show Arm/Leg Lock advanceds settings...", default=False)
    bpy.types.Scene.show_head_lock_advanced = BoolProperty(name='Head Lock Advanced Operators', description='Show Head Lock advanced settings...', default=False)
    bpy.types.Scene.show_snap_pole_advanced = BoolProperty(name='Snap Pole Advanced Operators', description='Show Snap Pole advanced settings...', default=False)
    bpy.types.Scene.show_footroll_advanced = BoolProperty(name='Foot Roll Break advanced settings', description='Show Foot Roll Break advanced settings...', default=False)
    bpy.types.Scene.arp_layers_set_render = BoolProperty(name="Set Render Visibility", description="Set objects visibility for rendering as well (not only viewport)", default=False)  
    bpy.types.Scene.arp_layers_show_exclu = BoolProperty(name="Show Exclusive Toggle", description="Show the exclusive visibility toggle of rig layers")
    bpy.types.Scene.arp_layers_show_select = BoolProperty(name="Show Select Toggle", description="Show the select toggle of rig layers")
    bpy.types.Scene.arp_layers_animated = BoolProperty(name="Animated Layers", description="Update animated rig layers visibility on each frame")   
    bpy.types.Scene.arp_spline_snap_indiv = BoolProperty(name='Snap Indiv Controllers', description='Snap Spline IK individual controllers too for better match.\nCan lead to weird results when moving master controllers after snapping')
    bpy.types.Scene.arp_spline_snap_iter_max = IntProperty(name='Max Iterations', description='Maximal iterations when snapping the  IK chain to FK. The higher, the more accurate but slower\nWarning, high values can take forever!', default=25, min=1, max=200)
    bpy.types.Scene.arp_spline_snap_precision = IntProperty(name='Precision', description='Decimal precision when snapping the IK chain to FK. The higher, the more accurate but slower\nWarning, high values can take forever!', default=3, min=1, max=200)
    

def unregister():
    from bpy.utils import unregister_class

    for cls in classes:
        try:
            unregister_class(cls)
        except:
            pass
        
    bpy.app.handlers.frame_change_post.remove(rig_layers_anim_update) 
    
    try:# errors when rig_tools and arp are installed together
        del bpy.types.Object.layers_sets
        del bpy.types.Object.layers_sets_idx
        del bpy.types.Scene.show_ik_fk_advanced
        del bpy.types.Scene.show_limb_lock_advanced
        del bpy.types.Scene.show_head_lock_advanced
        del bpy.types.Scene.show_snap_pole_advanced
        del bpy.types.Scene.show_footroll_advanced
        del bpy.types.Scene.arp_layers_set_render
        del bpy.types.Scene.arp_layers_show_exclu
        del bpy.types.Scene.arp_layers_show_select    
        del bpy.types.Scene.arp_layers_animated
        del bpy.types.Scene.arp_spline_snap_indiv
        del bpy.types.Scene.arp_spline_snap_iter_max
        del bpy.types.Scene.arp_spline_snap_precision
    except:
        pass
    
    