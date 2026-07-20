import bpy, bmesh, math, re, operator, os, difflib, csv, ast, copy
from bpy.types import Operator, PropertyGroup, Menu, Panel
from bpy.props import StringProperty, FloatProperty, IntProperty, BoolProperty, FloatVectorProperty, EnumProperty
from math import degrees, pi, radians, ceil, sqrt
from bpy.types import Panel, UIList
import mathutils
from mathutils import Vector, Euler, Matrix
from . import auto_rig
from .utils import *
        
        
#print ("\n Starting Auto-Rig Pro: Remap... \n")

##########################  CLASSES  ##########################

# Bones collection
class ARP_UL_items(UIList):

    @classmethod
    def poll(cls, context):
        return (context.scene.source_action != '' and context.scene.source_rig != '' and context.scene.target_rig != '')

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        split = layout.split(factor=1.0)
        split.prop(item, "source_bone", text="", emboss=False, translate=False)
        split = layout.split(factor=1.0)
        split.prop(item, "name", text="", emboss=False, translate=False)

    def invoke(self, context, event):
        pass


class ARP_MT_remap_import(Menu):    
    bl_label = "Import built-in presets list"
    
    custom_presets = []
    
    def draw(self, _context):
        layout = self.layout
        layout.operator("arp.import_config_preset", text="Advanced Skeleton (FK Arms, IK Legs)").preset_name = "advanced_skeleton"
        layout.operator("arp.import_config_preset", text="Auto-Rig Pro (FK Arms, IK Legs)").preset_name = "arp"
        layout.operator("arp.import_config_preset", text="Character Creator/ ActorCore (FK Arms, IK Legs)").preset_name = "character_creator"
        layout.operator("arp.import_config_preset", text="DAZ (FK Arms, IK Legs)").preset_name = "daz"
        layout.operator("arp.import_config_preset", text="DeepMotion (FK Arms, IK Legs)").preset_name = "deepmotion"
        layout.operator("arp.import_config_preset", text="Heat (FK Arms, IK Legs)").preset_name = "heat_ik"
        layout.operator("arp.import_config_preset", text="Heat (FK Arms, FK Legs)").preset_name = "heat_fk"
        layout.operator("arp.import_config_preset", text="MB Lab (FK Arms, IK Legs)").preset_name = "mblab"
        layout.operator("arp.import_config_preset", text="Mixamo (FK Arms, IK Legs)").preset_name = "mixamo_fbx_ik"
        layout.operator("arp.import_config_preset", text="Mixamo (FK Arms, FK Legs)").preset_name = "mixamo_fk"
        layout.operator("arp.import_config_preset", text="Mixamo (IK Arms, IK Legs)").preset_name = "mixamo_ik" 
        layout.operator("arp.import_config_preset", text="Mocopi (FK Arms, IK Legs)").preset_name = "mocopi" 
        layout.operator("arp.import_config_preset", text="Move One AI (FK Arms, IK Legs)").preset_name = "moveoneai" 
        layout.operator("arp.import_config_preset", text="Perception Neuron (FK Arms, IK Legs)").preset_name = "perception_neuron"
        layout.operator("arp.import_config_preset", text="Rigify (FK Arms, IK Legs)").preset_name = "rigify"
        layout.operator("arp.import_config_preset", text="Rokoko (FK Arms, IK Legs)").preset_name = "rokoko_legs_ik"
        layout.operator("arp.import_config_preset", text="Rokoko v2 (FK Arms, IK Legs)").preset_name = "rokoko_legs_ik_2"
        layout.operator("arp.import_config_preset", text="Unity Fbx").preset_name = "unity_export"
        layout.operator("arp.import_config_preset", text="Unreal Mannequin (FK Arms, IK Legs)").preset_name = "unreal_mannequin_remap"
        layout.operator("arp.import_config_preset", text="Xsens (FK Arms, IK Legs)").preset_name = "xsens"
		
        if len(self.custom_presets):
            layout.label(text='__________')
            
        for cp in self.custom_presets:
            op = layout.operator("arp.import_config_preset", text=cp.title()).preset_name = 'CUSTOM_'+cp      


class ARP_MT_remap_export(Menu):   
    bl_label = "Export as custom preset"
    
    def draw(self, _context):   
        layout = self.layout
        layout.operator("arp.remap_export_preset", text="Save as New Preset")  
        
        
class ARP_OT_remap_export_preset(Operator):
    """Export as custom preset"""
    
    bl_idname = "arp.remap_export_preset"
    bl_label = "Export Preset"
 
    preset_name: StringProperty(default='RemapPreset')
    valid_directory = True
    
    def invoke(self, context, event):
        # get filepath
        custom_dir = get_prefs().remap_presets_path
        if not (custom_dir.endswith("\\") or custom_dir.endswith('/')):
            custom_dir += '/'          
        
        try:
            os.listdir(custom_dir)
        except:
            self.valid_directory = False
    
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=400)
        
    
    def draw(self, context):
        layout = self.layout
        if self.valid_directory == False:
            layout.label(text="The preset directory is not set yet or doesn't exist,", icon='ERROR')
            layout.label(text="        where to store preset files?")
            layout.prop(context.preferences.addons['auto_rig_pro-master'].preferences, "remap_presets_path", text="Custom Presets Path")
            
        layout.prop(self, "preset_name", text="Preset Name")
        
        
    def execute(self, context):
        # get filepath
        custom_dir = get_prefs().remap_presets_path
        if not (custom_dir.endswith("\\") or custom_dir.endswith('/')):
            custom_dir += '/'          
        
        try:
            os.listdir(custom_dir)
        except:            
            self.report({'ERROR'}, 'The custom presets directory seems invalid: '+custom_dir+'\nCheck the path in the addon preferences')
            return
        
        
        filepath = custom_dir+self.preset_name
        
        # export
        _export_config(filepath)
        
        # update list
        update_remap_presets()
        
        return {'FINISHED'}        
        
        
class ARP_OT_clear_tweaks(Operator):  
    """Clear interactive tweaks"""

    bl_idname = "arp.retarget_clear_tweaks"
    bl_label = "retarget_clear_tweaks"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.scene.source_rig != "":
            if get_object(context.scene.source_rig):
                return True

    def execute(self, context):        
        try:
            _clear_interactive_tweaks()

        finally:
            pass
        return {'FINISHED'}
        
        
class ARP_OT_synchro_select(Operator):    
    """Select in the bones list the active bone in the viewport"""

    bl_idname = "arp.retarget_synchro_select"
    bl_label = "synchro_select"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == "POSE"

    def execute(self, context):
        scn = context.scene
        try:
            if len(context.selected_pose_bones):
                selected_pbone = context.selected_pose_bones[0]
                for idx, bone_item in enumerate(scn.bones_map_v2):
                    if bone_item.name == selected_pbone.name or bone_item.source_bone == selected_pbone.name:
                        scn.bones_map_index = idx

        finally:
            pass
        return {'FINISHED'}


class ARP_OT_freeze_armature(Operator):
    """Clear animation datas from the armature object and initialized its transforms. Preserve bones animation"""

    bl_idname = "arp.freeze_armature"
    bl_label = "freeze_armature"
    bl_options = {'UNDO'}

    arm : StringProperty(default="")
    child_bone_par_dict = {}                        

    @classmethod
    def poll(cls, context):
        if context.scene.source_rig != "":
            if get_object(context.scene.source_rig):
                return True


    def execute(self, context):
        if get_object(context.scene.source_rig) == None:
            message = "Source armature not found"
            self.report({'ERROR'}, message)
            return {'FINISHED'}

        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False

        try:
            _freeze_armature(self, self.arm)

        finally:
            context.preferences.edit.use_global_undo = use_global_undo
        return {'FINISHED'}


class ARP_OT_redefine_rest_pose(Operator):
    """If the source and target armatures have different rest poses, click this button to change the source armature rest pose, so that it looks like the target armature.\nNecessary for accurate retargetting.\nClick Apply to complete"""

    bl_idname = "arp.redefine_rest_pose"
    bl_label = "Redefine Rest Pose"
    bl_options = {'UNDO'}
    
    preserve: BoolProperty(default=True, name='Preserve', description='If enabled, the actual rest pose of the source armature is preserved. It only takes a snapshot of the new pose, and use it to offset the bones transforms when retargetting.\nIf disabled, the actual rest pose is modified, and its animation is re-baked based on the new rest pose')
    rest_pose: EnumProperty(items=(('REST', 'Rest Pose', 'Use the actual rest pose'), ('CURRENT', 'Current Pose', 'Use the current frame pose as rest pose'), ('SAVED', 'Saved', 'Use the modified saved rest pose as rest pose')), default="REST", name="Use Rest Pose", description="Set the rest pose")
    is_arp_armature: BoolProperty(default=False)
    
    
    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.scene.source_action != '' and context.scene.source_rig != '' and context.scene.target_rig != '')
        
    def draw(self, context):
        layout = self.layout   
        #print(self.is_arp_armature)
        if self.is_arp_armature:
            layout.label(text='The source armature is an Auto-Rig Pro armature', icon='ERROR')
            layout.label(text='It is best to change the rest pose with the button "Apply Pose as Rest Pose"')
            layout.label(text='in the ARP main menu.')
            layout.separator()
            
        layout.prop(self, 'preserve')
        layout.prop(self, 'rest_pose', expand=True)
        
        if self.rest_pose == "CURRENT":
            layout.label(text="Use the current pose as rest pose.")
        elif self.rest_pose == "REST":
            layout.label(text="Use the actual rest pose of this armature")     
        elif self.rest_pose == "SAVED":
            layout.label(text="Use the previously saved rest pose (if any) as rest pose")
        layout.label(text="The pose will remain editable until the Apply button is clicked. To revert, click Cancel")
        
        
    def invoke(self, context, event):
        # is it an arp armature?
        self.is_arp_armature = False
        source_rig = get_object(context.scene.source_rig)
        if 'arp_updated' in source_rig.data.keys():
            self.is_arp_armature = True
    
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=450)

    def execute(self, context):

        if not sanity_check(self):
            return {'FINISHED'}

        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False

        try:
            bpy.ops.object.mode_set(mode='OBJECT')
            _redefine_rest_pose(self, context)

        finally:
            context.preferences.edit.use_global_undo = use_global_undo
        return {'FINISHED'}


def show_action_row(_col, _act_name):
        row2 = _col.row(align=True)        
        
        act = bpy.data.actions.get(_act_name)
        if act == None:# deleted action
            return
            
        if bpy.app.version >= (3,5,0):
            row2.prop(act, '["arp_remap"]', text='')
        else:# cannot display int props as boolean checkbox in previous Blender version
            icon_name = 'CHECKBOX_DEHLT'#'CHECKBOX_HLT'
            if act["arp_remap"] == True:
                icon_name = 'CHECKBOX_HLT'
            op1 = row2.operator('arp.toggle_action_remap', text='', icon=icon_name)
            op1.action_name = _act_name
        
        op = row2.operator('arp.delete_action', text='', icon = 'X')
        op.action_name = _act_name
        
        row2.label(text=' '+_act_name)

        
class ARP_OT_toggle_action_remap(Operator):
    """Enable or disable this action from export"""

    bl_idname = "arp.toggle_action_remap"
    bl_label = "toggle_action_remap"
   
    action_name : StringProperty(default="")

    def execute(self, context):      
        try:
            if self.action_name != "":
                act = bpy.data.actions.get(self.action_name)
                if act:
                    found_prop = False
                    if len(act.keys()):
                        if "arp_remap" in act.keys():
                            act["arp_remap"] = not act["arp_remap"]                           
                            found_prop = True
                    if not found_prop:
                        act["arp_remap"] = True

        finally:
            pass

        return {'FINISHED'}  


class ARP_OT_enable_all_actions(Operator):
    """Enable all actions for retargetting"""
    
    bl_idname = 'arp.remap_enable_all_actions'
    bl_label = ''
    
    def execute(self, context):
        
        for act in bpy.data.actions:
            act['arp_remap'] = True
      
        return {'FINISHED'}
        
    
class ARP_OT_disable_all_actions(Operator):
    """Disable all actions for retargetting"""
    
    bl_idname = 'arp.remap_disable_all_actions'
    bl_label = ''
   
    def execute(self, context):
        
        for act in bpy.data.actions:
            act['arp_remap'] = False
      
        return {'FINISHED'}
        

class ARP_OT_remap_export_act_list(Operator):
    """Export selected actions list"""
    
    bl_idname = 'arp.remap_export_act_list'
    bl_label = 'Export Actions List'
    
    filepath: StringProperty(subtype="FILE_PATH", default='py')
    
    def invoke(self, context, event):
        self.filepath = 'remap_actions.py'
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}   
   
    def execute(self, context):
        _export_act_list(self)
      
        return {'FINISHED'}
        
        
class ARP_OT_remap_import_act_list(Operator):
    """Import selected actions list"""
    
    bl_idname = 'arp.remap_import_act_list'
    bl_label = 'Import Actions List'
    
    filepath: StringProperty(subtype="FILE_PATH", default='py')
    
    def invoke(self, context, event):
        self.filepath = 'remap_actions.py'
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}   
   
    def execute(self, context):
        _import_act_list(self)
      
        return {'FINISHED'} 
        

class ARP_OT_batch_retarget(Operator):
    '''Select multiple source animations for retargetting.\nIf "In Place" is enabled, process and select only In Place actions'''

    bl_idname = "arp.batch_retarget"
    bl_label = ""
    bl_options = {'UNDO'}
    
    actions_list = []
    
    
    def invoke(self, context, event):  
        if len(bpy.data.actions) == 0:
            self.report({'ERROR'}, 'No actions found')
            return {'FINISHED'}            
      
        self.actions_list = []
        
        for act in bpy.data.actions:
            if not 'arp_remap' in act.keys():
                act['arp_remap'] = True
                
            if not act.name in self.actions_list:
                self.actions_list.append(act.name)
                
        wm = context.window_manager
        return wm.invoke_popup(self, width=450)
    
    
    def draw(self, context):
        layout = self.layout
        scn = context.scene
        
        layout.separator()
        layout.prop(scn, 'batch_retarget', text='Enable Multiple Animations Retargetting')        
        
        layout.separator()
        row = layout.column().row(align=True)
        row.operator('arp.remap_import_act_list', text='Import')
        row.operator('arp.remap_export_act_list', text='Export')        
        layout.separator()
        
        row = layout.row(align=True)
        row.enabled = scn.batch_retarget
        row.operator('arp.remap_enable_all_actions', text='Enable All', icon='CHECKMARK')
        row.operator('arp.remap_disable_all_actions', text='Disable All')
        
        layout.prop(scn, 'arp_remap_only_containing', text='Only Containing', icon='VIEWZOOM')
        
        for actname in self.actions_list:
        
            if scn.arp_remap_only_containing != '':
                if not scn.arp_remap_only_containing in actname:
                    continue
                    
            col = layout.column(align=True)
            col.enabled = scn.batch_retarget            
            show_action_row(col, actname)    
        
    
    def execute(self, context):
        return {'FINISHED'}


class ARP_OT_auto_scale(Operator):
    """Automatic scale of the source armature to fit the target armature height\nMay not work if the rest position is incorrect, the height is calculated on this basis. Scale manually otherwise."""

    bl_idname = "arp.auto_scale"
    bl_label = "auto_scale"
    bl_options = {'UNDO'}


    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.scene.source_action != '' and context.scene.source_rig != '' and context.scene.target_rig != '')

    def execute(self, context):

        #save current mode
        current_mode = context.mode
        active_obj_name = None
        try:
            active_obj_name = context.active_object.name
        except:
            pass

        if not sanity_check(self):
            return {'FINISHED'}

        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False

        try:
            #set to object mode
            bpy.ops.object.mode_set(mode='OBJECT')

            _auto_scale(self, context)

            #restore saved mode
            if current_mode == 'EDIT_ARMATURE':
                current_mode = 'EDIT'
            try:
                bpy.ops.object.mode_set(mode='OBJECT')
                set_active_object(active_obj_name)
                bpy.ops.object.mode_set(mode=current_mode)

            except:
                pass

        finally:
            context.preferences.edit.use_global_undo = use_global_undo

        return {'FINISHED'}


class ARP_OT_apply_offset(Operator):

    #tooltip
    """Add an offset"""

    bl_idname = "arp.apply_offset"
    bl_label = "apply_offset"
    bl_options = {'UNDO'}


    value : StringProperty(name="offset_value")

    @classmethod
    def poll(cls, context):
        return (context.active_object != None)

    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False

        try:
            #save current mode
            current_mode = context.mode
            active_obj = None
            try:
                active_obj = context.active_object
            except:
                pass
            #set to object mode
            bpy.ops.object.mode_set(mode='OBJECT')

            _apply_offset(self.value)

            #restore saved mode
            if current_mode == 'EDIT_ARMATURE':
                current_mode = 'EDIT'
            try:
                bpy.ops.object.mode_set(mode='OBJECT')
                set_active_object(active_obj.name)
                bpy.ops.object.mode_set(mode=current_mode)

            except:
                pass

        finally:
            context.preferences.edit.use_global_undo = use_global_undo
        return {'FINISHED'}


class ARP_OT_cancel_redefine(Operator):
    #tooltip
    """Cancel the rest pose edition"""

    bl_idname = "arp.cancel_redefine"
    bl_label = "cancel_redefine"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.active_object != None)

    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False

        try:
            _cancel_redefine()

        finally:
            context.preferences.edit.use_global_undo = use_global_undo

        return {'FINISHED'}


class ARP_OT_copy_bone_rest(Operator):

    #tooltip
    """Copy the selected bones rotation from the corresponding bones in the target armature (the bones list must be assigned properly first)"""

    bl_idname = "arp.copy_bone_rest"
    bl_label = "copy_bone_rest"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.active_object != None)

    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False

        try:
            _copy_bone_rest(self, context)

        finally:
            context.preferences.edit.use_global_undo = use_global_undo

        return {'FINISHED'}


class ARP_OT_copy_raw_coordinates(Operator):
    """Complete the rest pose edition (long animations may take a while to complete)"""

    bl_idname = "arp.copy_raw_coordinates"
    bl_label = "copy_raw_coordinates"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.active_object != None)

    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False
        try:
            _copy_raw_coordinates(self, context)

        finally:
            context.preferences.edit.use_global_undo = use_global_undo
            
        return {'FINISHED'}
        
        
class ARP_OT_save_pose_rest(Operator):
    """Complete the rest pose edition"""

    bl_idname = "arp.save_pose_rest"
    bl_label = "save_pose_rest"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.active_object != None)

    def execute(self, context):       
        try:
            _save_pose_rest(self)

        finally:
            pass
            
        return {'FINISHED'}


class ARP_OT_pick_object(Operator):

    #tooltip
    """Pick the selected object/bone"""

    bl_idname = "arp.pick_object"
    bl_label = "pick_object"
    bl_options = {'UNDO'}

    action : EnumProperty(
        items=(
                ('pick_source', 'pick_source', ''),
                ('pick_target', 'pick_target', ''),
                ('pick_bone', 'pick_bone', ''),
                ('pick_pole', 'pick_pole', '')
            )
        )

    @classmethod
    def poll(cls, context):
        return (context.active_object != None)

    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False

        try:
            _pick_object(self.action)

        finally:
            context.preferences.edit.use_global_undo = use_global_undo

        return {'FINISHED'}


class ARP_OT_export_config(Operator):
    """Export the bones mapping to file"""
    
    bl_idname = "arp.export_config"
    bl_label = "Export Mapping"
    bl_options = {'UNDO'}
    
    filter_glob: StringProperty(default="*.bmap", options={'HIDDEN'})
    filepath: StringProperty(subtype="FILE_PATH", default='bmap')
    
    @classmethod
    def poll(cls, context):
        return (context.active_object != None)
    
    def execute(self, context):
    
        _export_config(self.filepath)
        
        return {'FINISHED'}

    def invoke(self, context, event):
        self.filepath = 'remap_preset.bmap'
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class ARP_OT_import_config_preset(Operator):
    """Import bones mapping from the presets list"""
    bl_idname = "arp.import_config_preset"
    bl_label = "Import Mapping from Path"    
    
    filepath: StringProperty(subtype="FILE_PATH", default='bmap')
    preset_name: StringProperty(default='')
    clear_current: BoolProperty(default=True)
    
    @classmethod
    def poll(cls, context):
        return (context.active_object != None)
        
        
    def invoke(self, context, event):
        scn = context.scene        
        wm = context.window_manager   
        
        if len(scn.bones_map_v2):
            return wm.invoke_props_dialog(self, width=450)
        else:
            return self.execute(context)
        
   
    def draw(self, context):
        layout = self.layout        
        layout.prop(self, 'clear_current', text='Clear Current Bones List')
        
       
    def execute(self, context):
        # custom presets
        if self.preset_name.startswith('CUSTOM_'):
            custom_dir = get_prefs().remap_presets_path
            if not (custom_dir.endswith("\\") or custom_dir.endswith('/')):
                custom_dir += '/'
                
            try:
                os.listdir(custom_dir)
            except:
                self.report({'ERROR'}, 'The custom presets directory seems invalid: '+custom_dir+'\nCheck the path in the addon preferences')
                return
    
            self.filepath = custom_dir + self.preset_name[7:]+'.bmap'  
            
        # built-in presets
        else:
            file_dir = os.path.dirname(os.path.abspath(__file__))
            addon_directory = os.path.dirname(file_dir)
            self.filepath = addon_directory + "/remap_presets/"+self.preset_name+'.bmap'
        
        _import_config(self)
       
        return {'FINISHED'}

        
class ARP_OT_import_config(Operator):
    """Import bones mapping from file"""
    bl_idname = "arp.import_config"
    bl_label = "Import Mapping"
    
    #filename_ext = ".bmap"   
    filter_glob: StringProperty(default="*.bmap", options={'HIDDEN'})
    filepath: StringProperty(subtype="FILE_PATH", default='bmap')
    clear_current: BoolProperty(default=True)
    
    @classmethod
    def poll(cls, context):
        return (context.active_object != None)
    
    def draw(self, context):
        layout = self.layout    
        layout.label(text='Import Preset Settings:')
        layout.prop(self, 'clear_current', text='Clear Current Bones List')
    
    def execute(self, context):
        
        _import_config(self)
        
        return {'FINISHED'}

    def invoke(self, context, event):
        self.filepath = 'remap_preset.bmap'
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


def check_retargetting_inputs(self):
    context = bpy.context
    
    def log_error_state():
        try:
            self.safety_check_error = True
        except:
            pass    
    
    if not sanity_check(self):
        log_error_state()
        return {'FINISHED'}        
    '''
    # check armature validity    
    if self.source_rig == None:
        log_error_state()
        self.report({'ERROR'}, 'The source armature cannot be found in the scene')
        return {'FINISHED'}
    
    if self.target_rig == None:
        log_error_state()
        self.report({'ERROR'}, 'The target armature cannot be found in the scene')
        return {'FINISHED'}
    '''
    self.source_rig = get_object(context.scene.source_rig)
    self.target_rig = get_object(context.scene.target_rig)
    
    # check the source armature has animation
    err = False
    if self.source_rig.animation_data == None:
        err = True
    elif self.source_rig.animation_data.action == None:
        err = True
    if err:
        log_error_state()
        self.report({'ERROR'}, 'The source armature has no animation')
        return {'FINISHED'}

    self.frame_start, self.frame_end = int(self.source_rig.animation_data.action.frame_range[0]), int(self.source_rig.animation_data.action.frame_range[1])

    # check if a Root bone has been assigned    
    if self.unbind == False:
        found_root = False
        for item in context.scene.bones_map_v2:
            if item.set_as_root:
                found_root = True

                if item.name == '':
                    log_error_state()
                    self.report({'ERROR'}, 'The root bone has no target')
                    return {'FINISHED'}
                
        if not found_root:   
            log_error_state()
            self.report({'ERROR'}, 'The root bone must be marked first: "Set as Root"')
            return {'FINISHED'}
            
        
    
    # check for invalid arp bones
    target_armature = get_object(context.scene.target_rig).data
    c_traj = target_armature.bones.get("c_traj")
    c_pos = target_armature.bones.get("c_pos")
    
    if c_traj and c_pos:
        print("The target armature is an Auto-Rig Pro armature")
        for b in context.scene.bones_map_v2:
            if target_armature.bones.get(b.name):
                pbone = self.target_rig.pose.bones.get(b.name)
                if not b.name.startswith("c_") and not "cc" in pbone.keys() and not b.name.startswith("cc"):
                    self.invalid_arp_bones = True
                    break
          
    # check duplicates
    print("Checking duplicates...")
    target_bones_found = []    
    duplis_found = False
    for bone in context.scene.bones_map_v2:
        if bone.name == '' or bone.name == 'None':
            continue
        if not bone.name in target_bones_found:
            target_bones_found.append(bone.name)
        else:
            print(bone.name, "is set multiple times as target bone, clearning...")
            bone.name = ''
            duplis_found = True
            
    if duplis_found:       
        print('Some target bones were assigned multiple times, duplicates were cleared automatically')
        
        
def check_armature_init_transforms(self):
    if self.target_rig == None or self.source_rig == None:
        return
        
    current_selection_name = bpy.context.active_object.name if bpy.context.active_object else None
    
    if is_object_hidden(self.target_rig):
        unhide_object(self.target_rig)
    if is_object_hidden(self.source_rig):
        unhide_object(self.source_rig)
    
    for arm_obj in [self.target_rig, self.source_rig]:
        # is rotation initialized?        
        for axis in arm_obj.rotation_euler:
            if axis != 0.0:
                if arm_obj == self.source_rig:
                    self.source_rig_is_frozen = False
                elif arm_obj == self.target_rig:
                    self.target_rig_is_frozen = False
                    
        # is scale initialized?        
        for axis in arm_obj.scale:
            if axis != 1.0:
                # scale initialization can be skipped for the source rig
                #if arm_obj == self.source_rig:
                #    self.source_rig_is_frozen = False
                if arm_obj == self.target_rig:
                    self.target_rig_is_frozen = False        
        
        # is the armature object animated?    
        has_action = False
        if arm_obj.animation_data:
            if arm_obj.animation_data.action:
                has_action = True
                
        if has_action:
            slot_i = 0
            if bpy.app.version >= (4,4,0):
                slot_i = get_action_slot_idx(arm_obj.animation_data.action, arm_obj.animation_data.action_slot)
                
            for fcurve in get_action_fcurves(arm_obj.animation_data.action, slot_idx=slot_i, as_list=True):
                if not 'pose.bones' in fcurve.data_path:
                    if 'location' in fcurve.data_path or 'rotation' in fcurve.data_path or 'scale' in fcurve.data_path:
                        if arm_obj == self.source_rig:
                            self.source_rig_is_frozen = False
                        elif arm_obj == self.target_rig:
                            self.target_rig_is_frozen = False   

        # is the origin normalized?
        if arm_obj == self.source_rig:
            # enter Edit Mode
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            set_active_object(self.source_rig.name)
            
            bpy.ops.object.mode_set(mode='EDIT')
            
            for ebone in self.source_rig.data.edit_bones:
                if (self.source_rig.matrix_world @ ebone.head)[2] < -0.01:
                    self.source_origin_not_normalized = True
                    break
            
    # restore selection
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    set_active_object(current_selection_name)
        

def check_bones_names_length(self):
    scn = bpy.context.scene
    source_rig = get_object(scn.source_rig)
    if source_rig == None:
        self.too_long_bones_names = False
        return
        
    for b in source_rig.data.bones:
        if len(b.name) > 50:
            self.too_long_bones_names = True            
            return
            
    self.too_long_bones_names = False

        
def draw_menu_freeze(self, layout):
    scn = bpy.context.scene
    if scn.arp_show_freeze_warn == False:
        self.freeze_source = 'NO'
        self.freeze_target = 'NO'
        return
        
    text_show_freeze = 'Show freeze warning next time'
    freeze_was_proposed = False
    
    if not self.source_rig_is_frozen or not self.target_rig_is_frozen:
        freeze_info_text = ["         This may lead to issues in some cases. Freeze it first?", "         This will affect the animation transform values, but keep it the same visually."]
        
        if not self.source_rig_is_frozen:                
            layout.label(icon="INFO", text="Source armature rotation is not frozen: X, Y or Z values are different from 0 or 1")
            for txt in freeze_info_text:
                layout.label(text=txt)  

            layout.separator()                     
            layout.prop(self, 'freeze_source', expand=True)   
            freeze_was_proposed = True
            
        if not self.target_rig_is_frozen:
            layout.label(icon="INFO", text="Target armature transforms are not frozen: rotation or scale are different from 0 or 1")
            if self.source_rig_is_frozen:#only display addition text info if not already displayed
                for txt in freeze_info_text:
                    layout.label(text=txt) 
                    
            layout.separator()            
            layout.prop(self, 'freeze_target', expand=True)  
            freeze_was_proposed = True
            
    elif self.source_origin_not_normalized:
        layout.label(icon="INFO", text="Source armature origin seems incorrect, freeze it?")
        layout.label(text="(If not sure, first try without freezing. Then if the output animation is offset, enable it)")
        layout.prop(self, "force_source_freeze", expand=True)
        layout.separator()
        freeze_was_proposed = True
        
    if freeze_was_proposed:
        layout.prop(self, 'show_freeze_warn', text=text_show_freeze)
    
    layout.separator()
    layout.separator()


def draw_menu_max_chars_limit(self, layout):
    layout.label(text='Very long bones names! Retargetting may FAIL', icon='ERROR')
    layout.label(text='        Rename bones with shorter names')
    
            
class ARP_OT_bind_only(Operator):
    """Retarget, binding only without baking for quick preview"""

    bl_idname = "arp.retarget_bind_only"
    bl_label = ""
    bl_options = {'UNDO'}

    target_rig = None
    source_rig = None
    source_rig_is_frozen = True
    target_rig_is_frozen = True
    freeze_source: EnumProperty(items=(('YES', 'Yes, Please!', ''), ('NO', "No, Maybe Later", '')), default='NO', name='Freeze Source Armature')
    freeze_target: EnumProperty(items=(('YES', 'Yes, Please!', ''), ('NO', "No, Maybe Later", '')), default='NO', name='Freeze Target Armature')
    show_freeze_warn: BoolProperty(default=True)    
    too_long_bones_names: BoolProperty(default=False, description='Bones names length >50 will fail retargetting because temp bones are renamed when retargetting')
    child_bone_par_dict = {}                        
    
    invalid_arp_bones = None
    bind_only = True
    unbind : BoolProperty(default=False)
    safety_check_error = False    
    NLA_tweak_state = False
    NLA_muted = []
    
    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.scene.source_rig != "" and context.scene.target_rig != "")
    
    
    def invoke(self, context, event):
        scn = context.scene
        self.show_freeze_warn = scn.arp_show_freeze_warn
        
        wm = context.window_manager
        check_retargetting_inputs(self)
        check_armature_init_transforms(self)
        check_bones_names_length(self)
        self.NLA_tweak_state = nla_exit_tweak()# NLA tweak mode is not supported yet, always disable it        
        self.NLA_muted = nla_mute(get_object(scn.target_rig))
        
        if not self.unbind:# not relevant to freeze transforms when unbinding
            if self.invalid_arp_bones or \
                ((not self.source_rig_is_frozen or not self.target_rig_is_frozen) and scn.arp_show_freeze_warn) or \
                self.too_long_bones_names:
                return wm.invoke_props_dialog(self, width=450)
        
        if self.safety_check_error:
            return {'FINISHED'}

        return self.execute(context)
        
        
    def draw(self, context):
        layout = self.layout        
        draw_menu_freeze(self, layout)    
        if self.too_long_bones_names:
            draw_menu_max_chars_limit(self, layout)
        if self.invalid_arp_bones:
            layout.separator()
            layout.label(text='Warning!', icon='INFO')
            layout.label(text='The target armature is an Auto-Rig Pro armature, while some bones')
            layout.label(text='in the list are not controller (no "c_" prefix").')
            layout.label(text='Retargetting to non-controller bones can potentially break the rig. Continue?')

        layout.separator()


    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False

        try:
            scn = context.scene
            scn.arp_show_freeze_warn = self.show_freeze_warn
            
            #save current mode
            current_mode = context.mode
            active_obj = None
            try:
                active_obj = context.active_object
            except:
                pass
            
            # save to object mode
            bpy.ops.object.mode_set(mode='OBJECT')

            # execute  
            
            if not self.source_rig_is_frozen and self.freeze_source == 'YES':
                _freeze_armature(self, "source")
            if not self.target_rig_is_frozen and self.freeze_target == 'YES':
                _freeze_armature(self, "target")
            
            _retarget(self)
            
            # restore current mode
            try:
                set_active_object(active_obj.name)
            except:
                pass
            # restore saved mode
            if current_mode == 'EDIT_ARMATURE':
                current_mode = 'EDIT'

            try:
                bpy.ops.object.mode_set(mode=current_mode)
            except:
                pass


        finally:
            nla_restore_tweak(self.NLA_tweak_state)
            
            # NLA: unmute muted tracks
            if len(self.NLA_muted):      
                nla_unmute(get_object(scn.target_rig), self.NLA_muted)
                # set Replace mode
                get_object(scn.target_rig).animation_data.action_blend_type = 'REPLACE'
                
                
            context.preferences.edit.use_global_undo = use_global_undo

        return {'FINISHED'}


class ARP_OT_retarget(Operator):
    """Retarget the source armature action to the target armature"""

    bl_idname = "arp.retarget"
    bl_label = "Retarget"
    bl_options = {'UNDO'}

    frame_start : IntProperty(default=0, name="Frame Start", description="Bake from this frame")
    frame_end : IntProperty(default=10, name = "Frame End", description="Bake to this frame")
    target_rig = None
    source_rig = None
    source_rig_is_frozen = True
    target_rig_is_frozen = True
    freeze_source: EnumProperty(items=(('YES', 'Yes, Please!', ''), ('NO', "No, Maybe Later", '')), default='NO', name='Freeze Source Armature')
    freeze_target: EnumProperty(items=(('YES', 'Yes, Please!', ''), ('NO', "No, Maybe Later", '')), default='NO', name='Freeze Target Armature')
    show_freeze_warn: BoolProperty(default=True)
    fake_user_action: BoolProperty(default=False, description='Enable "Fake User" to the remapped action, so that it is not removed from the file later if not used.\nAutomatically enabled when retargetting multiple animations', name='Fake User')
    clean_fk_rot: BoolProperty(default=False, name='Clean FK Rotations (Slow)', description='Ensure single rotation axis for forearm and leg FK controllers (ARP armatures only)')
    clean_ik_pole: BoolProperty(default=False, name='Clean IK Poles', description='Remove IK pole bones keyframes below a given angle threshold')
    clean_ik_pole_angle: FloatProperty(default=5.0, name='Clean IK Pole Angle', description='Angle threshold')
    too_long_bones_names: BoolProperty(default=False)
    only_existing_keyframes: BoolProperty(default=False, name='Bake Only Existing Keyframes', description='Only bake existing keyframes instead of baking one keyrame per frame\nCan lead to incorrect results, especially with IK controllers -use it wisely')
    
    extract_root_motion: BoolProperty(default=False, name='Extract Root Motion (c_traj)', description='(Only for Auto-Rig Pro rigs)\nProject the pelvis location and rotation to the floor, to the c_traj bone')  
    loc_x: BoolProperty(default=True, description='Use X location (World space, left/right)')
    loc_y: BoolProperty(default=True, description='Use Y location (World space, forward/backward)')
    loc_z: BoolProperty(default=False, description='Use Z location (World space, height)')
    loc_z_offset: BoolProperty(default=True, description='Keep initial offset when applying Z location')   
    rotation: BoolProperty(default=True, description='Use rotation (World space)')
    forward_axis: EnumProperty(items=(
        ('X', 'X', 'X'),
        ('Y', 'Y', 'Y'),
        ('Z', 'Z', 'Z'),
        ('-X', '-X', '-X'),
        ('-Y', '-Y', '-Y'),
        ('-Z', '-Z', '-Z'),
        ), description='The c_root_master axis pointing forward, that will be used to orient the c_traj Y axis', default='Z')
        
    source_origin_not_normalized = False
    force_source_freeze : EnumProperty(items=(('YES', 'Yes, Please!', ''), ('NO', "No, Maybe Later", '')), default='NO', description="Freeze the source armature", name="Freeze Source Armature")
    interpolation_type : EnumProperty(items=(('LINEAR', 'Linear', 'Linear interpolation between two keyframes'), ('BEZIER', 'Bezier', 'Bezier interpolation between two keyframes'), ('CONSTANT', 'Constant', 'Constant interpolation between two keyframes')), name="Keyframe Interpolation")
    handle_type: EnumProperty(items=(('DEFAULT', 'Default', 'Default handle type'), ('AUTO_CLAMPED', 'Auto Clamped', ' Automatic handles that create smooth curves which only change direction at keyframes'), ('AUTO', 'Auto', 'Automatic handles that create smooth curves'), ('VECTOR', 'Vector', 'Automatic handles that create straight lines'), ('ALIGNED', 'Aligned', 'Manually set handle with rotation locked together with its pair'), ('FREE', 'Free', 'Completely independent manually set handle')), name="Keyframe Handles")

    child_bone_par_dict = {}                        
    safety_check_error = False
    invalid_arp_bones = None
    bind_only = False
    unbind : BoolProperty(default=False)
    NLA_tweak_state = False
    NLA_muted = []
    
    
    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.scene.source_rig != "" and context.scene.target_rig != "")
    
    
    def invoke(self, context, event):
        scn = context.scene
        self.show_freeze_warn = scn.arp_show_freeze_warn
        
        wm = context.window_manager
        self.force_source_freeze = 'NO'
        check_retargetting_inputs(self)
        check_armature_init_transforms(self)
        check_bones_names_length(self)
        self.NLA_tweak_state = nla_exit_tweak()        
        self.NLA_muted = nla_mute(get_object(scn.target_rig))
        
        # Batch retargeting:
        # check the actions list is not empty
        if scn.batch_retarget:
            found_at_least_one = False
            
            for act in bpy.data.actions:
            
                # filter only containing
                if scn.arp_remap_only_containing != '':
                    if not scn.arp_remap_only_containing in act.name: continue
                        
                if 'arp_remap' in act.keys() and act['arp_remap'] == True:
                    found_at_least_one = True
                    break
                        
            if not found_at_least_one:
                self.report({'ERROR'}, 'No actions to bake, check Multiple Source Anim...')
                return {'FINISHED'}
                
                
            # batch convert In Place actions
            if scn.arp_retarget_in_place:
            
                for act in bpy.data.actions:
                    # filter already In Place actions
                    if '_IN_PLACE' in act.name: continue
                    
                    # filter only containing
                    if scn.arp_remap_only_containing != '':# filter only containing
                        if not scn.arp_remap_only_containing in act.name: continue
                    
                    # filter selected ones
                    if 'arp_remap' in act.keys() and act['arp_remap'] == True:
                        # convert in place
                        act_in_place = convert_in_place(True, act_name=act.name, act_slot=0)
                        # select for export
                        act_in_place['arp_remap'] = True
                        # deselect base action
                        act['arp_remap'] = False
            
        
        if self.safety_check_error:
            return {'FINISHED'}
                
        return wm.invoke_props_dialog(self, width=450)
        
        
    def draw(self, context):
        layout = self.layout
        draw_menu_freeze(self, layout)
        if self.too_long_bones_names:
            draw_menu_max_chars_limit(self, layout)
            
        if not context.scene.batch_retarget:
            row = layout.column().row(align=True)
            row.prop(self, 'frame_start')
            row.prop(self, 'frame_end')
        
        layout.use_property_split = True
        layout.separator()
        col = layout.column()
        col.prop(self, 'interpolation_type')
        col.prop(self, 'handle_type')
        col.prop(self, 'only_existing_keyframes')

        if self.invalid_arp_bones:
            layout.separator()
            layout.label(text='Warning!', icon='INFO')
            layout.label(text='The target armature is an Auto-Rig Pro armature, while some bones')
            layout.label(text='in the list are not controller (no "c_" prefix).')
            layout.label(text='Retargetting to non-controller bones can potentially break the rig. Continue?')            
        
        
        if not context.scene.batch_retarget:
            layout.separator()
            layout.prop(self, 'fake_user_action') #icon='FAKE_USER_ON', text='')
            
        layout.prop(self, 'clean_fk_rot')
        row = layout.column().row()
        row.prop(self, 'clean_ik_pole')
        row1 = row.row()
        row1.prop(self, 'clean_ik_pole_angle', text='Angle')
        row1.enabled = self.clean_ik_pole
        layout.separator()
        
        layout.prop(self, 'extract_root_motion', text='Extract Root Motion', toggle=1)
        if self.extract_root_motion:
            col = layout.column()
            row = col.row()
            row.prop(self, 'loc_x', text='Location X')
            row.prop(self, 'loc_y', text='Y')
            row.prop(self, 'loc_z', text='Z')
            col = layout.column()
            col.prop(self, 'loc_z_offset', text='Location Z Offset')
            col.enabled = self.loc_z
            col = layout.column()
            col.prop(self, 'rotation', text='Rotation')
            col = col.column()
            col.enabled = self.rotation
            row = col.row(align=True)
            row.prop(self, 'forward_axis', text='Pelvis Forward Axis', expand=True)        
            col.separator()
        

    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False
        
        try:           
            scn = context.scene
            scn.arp_show_freeze_warn = self.show_freeze_warn
            
            # save current mode
            current_mode = context.mode
            active_obj = None
            try:
                active_obj = context.active_object
            except:
                pass
                
            # save map index
            b_index = scn.bones_map_index
                
            # save to object mode
            bpy.ops.object.mode_set(mode='OBJECT')

            # execute     
          
            if (not self.source_rig_is_frozen and self.freeze_source == 'YES') or self.force_source_freeze == 'YES':
                _freeze_armature(self, "source")
            if (not self.target_rig_is_frozen and self.freeze_target == 'YES'):
                _freeze_armature(self, "target")
            
            _retarget(self)
            
            # restore map index
            scn.bones_map_index = b_index
            
            # restore current mode
            try:
                set_active_object(active_obj.name)
            except:
                pass
            # restore saved mode
            if current_mode == 'EDIT_ARMATURE':
                current_mode = 'EDIT'

            try:
                bpy.ops.object.mode_set(mode=current_mode)
            except:
                pass


        finally:
            nla_restore_tweak(self.NLA_tweak_state)
                    
            # NLA: unmute muted tracks
            if len(self.NLA_muted):      
                nla_unmute(get_object(scn.target_rig), self.NLA_muted)
                # set Replace mode
                get_object(scn.target_rig).animation_data.action_blend_type = 'REPLACE'             
            
            context.preferences.edit.use_global_undo = use_global_undo

        return {'FINISHED'}

        
class ARP_OT_mirror_bones_list(Operator):
    """Mirror the bones list, from left to right or vice versa"""

    bl_idname = "arp.mirror_bones_list"
    bl_label = "mirror_bones_list"
    bl_options = {'UNDO'}
    
    mirror_dir: EnumProperty(items=( ('LEFT_TO_RIGHT','Left to Right', 'Left to Right'), ('RIGHT_TO_LEFT','Right to Left','Right to Left') ), 
        description="Mirror direction, from left to right or right to left")
    
    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=450)
        
    def draw(self, context):
        layout = self.layout
        layout.prop(self, 'mirror_dir', expand=True)
    
    def execute(self, context):
        scn = context.scene
        
        _mirror_bones_list(self.mirror_dir)
        
        return {'FINISHED'}

        
class ARP_OT_build_bones_list(Operator):
    """Build the source and target bones list, and try to match their names with Auto-Rig Pro or any other armature"""

    bl_idname = 'arp.build_bones_list'
    bl_label = 'build_bones_list'
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.scene.source_action != '' and context.scene.source_rig != '' and context.scene.target_rig != '')

    def execute(self, context):
        scn = context.scene
        
        if not sanity_check(self):
            return {'FINISHED'}
        
        if bpy.data.actions.get(get_source_action_name()) == None:
            self.report({'ERROR'}, "Source action '"+get_source_action_name()+"' cannot be found, set again the Source Armature object to fix it") 
            return {'FINISHED'}
            
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False

        try:
            #save current mode
            current_mode = context.mode
            active_obj = None
            try:
                active_obj = context.active_object
            except:
                pass
            #save to object mode
            bpy.ops.object.mode_set(mode='OBJECT')

            #execute function
            _build_bones_list()

            #restore current mode
            try:
                bpy.ops.object.select_all(action='DESELECT')
                set_active_object(active_obj.name)
            except:
                pass
                #restore saved mode
            if current_mode == 'EDIT_ARMATURE':
                current_mode = 'EDIT'

            try:
                bpy.ops.object.mode_set(mode=current_mode)
            except:
                pass

        finally:
            context.preferences.edit.use_global_undo = use_global_undo

        return {'FINISHED'}


class ARP_OT_remap_update(Operator):
    """Update Remap settings to latest version"""
    
    bl_idname = "arp.remap_update"
    bl_label = "remap_update"

    def execute(self, context):
        scn = context.scene
        
        # copy old bones_map settings to new bones_map_v2
        scn.arp_remap_allow_root_update = False# disable it before assigning the set root value, otherwise it's interfering
        
        if 'bones_map' in scn.keys():
            #   clear current bones_map_v2(but supposed to be blank at this point...)
            if len(scn.bones_map_v2):
                i = len(scn.bones_map_v2)
                while i >= 0:
                    scn.bones_map_v2.remove(i)
                    i -= 1    
                
            # copy
            for item in scn.bones_map:
                item_v2 = scn.bones_map_v2.add()
                for prop in dir(item):
                    if prop.startswith('__') or prop == 'bl_rna' or prop == 'rna_type':# invalid props
                        continue
                    if prop in dir(item_v2):                        
                        val = getattr(item, prop)
                        setattr(item_v2, prop, val)
                        
        # copy old source_nodes_name_string to remap_source_nodes
        #   clear current remap_source_nodes(but supposed to be blank at this point...)
        if len(scn.remap_source_nodes):
            i = len(scn.remap_source_nodes)
            while i >= 0:
                scn.remap_source_nodes.remove(i)
                i -= 1    
            
        # copy
        if scn.source_nodes_name_string != '':
            for n in scn.source_nodes_name_string.split('+'):
                item = scn.remap_source_nodes.add()
                item.source_name = n
                        
        # flag as updated (hacky...)
        first_item = scn.bones_map[1]
        first_item.x_inv = True
        
        scn.arp_remap_allow_root_update = True# disable it before assigning the set root value, otherwise it's interfering
        
        return {'FINISHED'}
    
    
        
############ FUNCTIONS ##############################################################
def sanity_check(self):
    # check if both source and target armature are in the scene
    src_rig = get_object(bpy.context.scene.source_rig)
    tar_rig = get_object(bpy.context.scene.target_rig)    
    
    if src_rig == None:
        self.report({'ERROR'}, "Source Armature not found")
        return False   
    if tar_rig == None:
        self.report({'ERROR'}, "Target Armature not found")
        return False   
    
    if src_rig.type != "ARMATURE":
        self.report({'ERROR'}, "Source Object is not an armature")
        return False   
    
    if tar_rig.type != "ARMATURE":
        self.report({'ERROR'}, "Target Object is not an armature")
        return False   
        
    return True
  

# Global utilities---------------------------------------------------------
def add_empty(location_empty = (0,0,0), name_string="name_string"):
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.empty_add(type='PLAIN_AXES', radius=1, location=(location_empty), rotation=(0, 0, -0))
    bpy.context.object.name = name_string

    
def update_remap_presets():
    presets_directory = get_prefs().remap_presets_path
    
    if not (presets_directory.endswith("\\") or presets_directory.endswith('/')):
        presets_directory += '/'
    
    #   if the folder cannot be found, try to create it
    if not os.path.exists(presets_directory):
        try:            
            os.makedirs(presets_directory)
        except:
            pass
    
    try:
        os.listdir(presets_directory)
    except:
        #print("The custom presets directory seems invalid:", presets_directory)
        return

    for file in os.listdir(presets_directory):
        if not file.endswith(".bmap"):
            continue
            
        preset_name = file.replace('.bmap', '')
        
        if preset_name in ARP_MT_remap_import.custom_presets:
            continue

        ARP_MT_remap_import.custom_presets.append(preset_name)


def save_source_action(source_rig):
    scn = bpy.context.scene
    scn.source_action = source_rig.animation_data.action.name
    if bpy.app.version >= (4,4,0) and len(source_rig.animation_data.action.slots):# get active action slot too
        scn.source_action += '[%%%]'+source_rig.animation_data.action_slot.identifier


def get_source_action_name(get_slot=False):
    splitname = bpy.context.scene.source_action.split('[%%%]')
    source_act_name = splitname[0]
    
    if get_slot:
        source_slot = 0
        if len(splitname) > 1:
            source_slot_idname = splitname[1]  
            source_slot = get_action_slot_idx(bpy.data.actions.get(source_act_name), bpy.data.actions.get(source_act_name).slots.get(source_slot_idname))
            
        return source_act_name, source_slot
        
    else:
        return source_act_name


# Main funcs-------------------------------------------------------------
def _export_act_list(self):
    print('Export actions list...')
    
    acts = []
    
    for act in bpy.data.actions:
        selected = False
        if 'arp_remap' in act.keys():
            selected = act['arp_remap']
        
        if selected:
            acts.append(act.name)
            
    scn = bpy.context.scene
    fp = self.filepath
       
    if not (fp.endswith('.py')):
        fp += '.py'

    fp = os.path.abspath(fp)# automatically adds the driver letter if the path does not contain any
    #print(fp)
    if not os.path.exists(os.path.dirname(fp)):
        try:
            os.makedirs(os.path.dirname(fp))
        except:
            pass
            
    file = open(fp, 'w', encoding='utf8', newline='\n')
    
    file.write(str(acts))
    file.close()
    print("Remap actions list successfully exported!")
    print(acts)
    print(fp)
    
    
def _import_act_list(self):
    print('Import actions list...')
    fp = os.path.abspath(self.filepath)
    
    if not (fp.endswith('.py') or fp.endswith('.py')):
        fp += '.py'
 
    if not os.path.exists(os.path.dirname(fp)):
        print("File not found.")
        return
        
    file = None
    actlist = None
    try:
        file = open(fp, 'r') if sys.version_info >= (3, 11) else open(fp, 'rU')
        file_lines = file.readlines()
        actlist= str(file_lines[0])
    except:
        print("Cannot read file")
        return        
    
    acts = ast.literal_eval(actlist)
    
    for actname in acts:
        act = bpy.data.actions.get(actname)
        if act:
            act['arp_remap'] = True
            
    file.close()
   
    print("Remap actions list successfully imported!")
    print(acts)
    print(fp)
    
    
def _copy_bone_rest(self,context):
    scene = context.scene
    current_frame = bpy.context.scene.frame_current#save current frame
    target_rig = get_object(scene.target_rig)
    source_rig = get_object(scene.source_rig)
    target_bone_name = None

    for bone in context.selected_pose_bones:
        #get the target bone
        for b in scene.bones_map_v2:
            if b.source_bone == bone.name:
                target_bone_name = b.name

        if target_bone_name == None:
            continue

        if target_bone_name == "" or target_rig.pose.bones.get(target_bone_name) == None:
            continue

        target_bone = target_rig.pose.bones[target_bone_name]
        vec = (target_bone.tail - target_bone.head)

        #refresh
        bpy.context.scene.frame_set(bpy.context.scene.frame_current)

        empty_loc = (source_rig.matrix_world @ bone.head) + target_rig.matrix_world @ (vec*10000)

        add_empty(location_empty=empty_loc, name_string=bone.name+"_EMP")
        emp_track_obj = get_object(bone.name+"_EMP")
        emp_track_obj['arp_remap_emp_track'] = 1
        set_active_object(source_rig.name)
        bpy.ops.object.mode_set(mode='POSE')

        new_cns = bone.constraints.new('DAMPED_TRACK')
        new_cns.name = 'damped_track_REMAP'
        new_cns.target = emp_track_obj

        #refresh
        bpy.context.scene.frame_set(bpy.context.scene.frame_current)

        # store the bone transforms
        bone_mat = bone.matrix.copy()

        #clear constraints
        cns = bone.constraints.get('damped_track_REMAP')
        if cns:
            bone.constraints.remove(cns)

        # restore the transforms
        bone.matrix = bone_mat

    #clear empties helpers    
    for obj in bpy.data.objects:
        if 'arp_remap_emp_track' in obj.keys():
            delete_object(obj)


def _pick_object(action):
    obj = bpy.context.object
    scene = bpy.context.scene

    if action == "pick_source":
        scene.source_rig = obj.name
    elif action == "pick_target":
        scene.target_rig = obj.name
    elif action == 'pick_bone' or action == 'pick_pole':
        bname = ''
        try:            
            if bpy.context.mode == 'POSE':
                bname = bpy.context.selected_pose_bones[0].name
            elif bpy.context.mode == 'EDIT_ARMATURE':
                bname = bpy.context.selected_editable_bones[0].name            
        except:
            print("can't pick bone")

        if action == 'pick_pole':        
            scene.bones_map_v2[scene.bones_map_index].ik_pole = bname
        elif action == 'pick_bone':
            scene.bones_map_v2[scene.bones_map_index].name = bname      
            
     
def _freeze_armature(self, arm_type):
    print("Freeze armature:", arm_type)
    context = bpy.context
    scn = context.scene
    saved_frame = scn.frame_current
    scn.frame_set(context.scene.frame_current)# update hack, not sure it's necessary there

    # Disable auto-keying
    scn.tool_settings.use_keyframe_insert_auto = False

    arm_name = ""
    if arm_type == "source":
        arm_name = scn.source_rig
    elif arm_type == "target":
        arm_name = scn.target_rig
    
    armature = get_object(arm_name)
    
    set_active_object(armature.name)
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    set_active_object(armature.name)
   
    base_arm_name = armature.name
    
    # the target armature is not supposed to be animated
    if arm_type == "target":
        anim_data = armature.animation_data
        if anim_data:
            if anim_data.action:
                anim_data.action = None
                
        # if it's an ARP armature as target: init rot and scale, reset_stretches() et set_inverse()
        is_arp_armature = False
        if armature.data.bones.get("c_traj") and armature.data.bones.get("c_pos"):
            is_arp_armature = True
            
        if is_arp_armature:
            auto_rig.init_arp_scale(self, armature.name)
            auto_rig._reset_stretches()
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
            bpy.ops.object.mode_set(mode='POSE')
            auto_rig._set_inverse()
            bpy.ops.object.mode_set(mode='OBJECT')
            return
                
    # get the current action name
    base_action_name = None   
    if armature.animation_data:
        if armature.animation_data.action:
            base_action_name = armature.animation_data.action.name
        else:
            print("Armature", armature.name, "has no action")
    else:
        print("Armature", armature.name, "has no action")

    # Unparent skinned meshes
    skinned_meshes = []
    parented_meshes = []

    #   meshes parented to bones support (no skinning): store meshes
    meshes_parented_to_bones = {}
    for obj in bpy.data.objects:
        if (obj.type != 'MESH' and obj.type != "EMPTY") or is_object_hidden(obj):
            continue
        # obj parented to bone
        if obj.parent:
            if obj.parent == armature and obj.parent_type == "BONE":
                if obj.parent_bone != "":
                    meshes_parented_to_bones[obj.name] = obj.parent_bone

    #   skinned meshes
    if len(armature.children):
        for obj in armature.children:
            if obj.type == "MESH":
                obj_mat = obj.matrix_world.copy()
                obj.parent = None
                bpy.context.evaluated_depsgraph_get().update()
                obj.matrix_world = obj_mat
                parented_meshes.append(obj.name)

    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        for mod in obj.modifiers:
            if mod.type == "ARMATURE":
                if mod.object == bpy.context.active_object:
                    skinned_meshes.append(obj.name)


    # Freeze 
    # temporarily zero out location
    saved_loc = armature.location.copy()   
    armature.location = [0,0,0]
   
    # duplicate
    bpy.ops.object.duplicate_move(OBJECT_OT_duplicate={"linked":False, "mode":'TRANSLATION'}, TRANSFORM_OT_translate={"value":(0, 0, 0), "remove_on_cancel":False, "release_confirm":False, "use_accurate":False})
    
    duplicate_armature = get_object(bpy.context.active_object.name)
    if base_action_name:
        duplicate_armature.animation_data.action.name = base_action_name + "_TEMP_COPY"

    # Constrain to the first armature
    bpy.ops.object.mode_set(mode='POSE')

    for pbone in duplicate_armature.pose.bones:
        cns = pbone.constraints.new('COPY_TRANSFORMS')
        cns.target = get_object(base_arm_name)
        cns.subtarget = pbone.name
        cns.name = "arp_remap_temp"
        
        # add scale constraint to fix scale of armature object leading to incorrect bone scaling
        cns_scale = pbone.constraints.new('COPY_SCALE')
        cns_scale.target = get_object(base_arm_name)
        cns_scale.subtarget = pbone.name
        cns_scale.name = "arp_remap_temp"
        cns_scale.target_space = "POSE"
        cns_scale.owner_space = "WORLD"

    # Set frame 0  
    scn.frame_set(0)

    # Remove keyframes on object level
    if base_action_name:
        slot_i = 0
        if bpy.app.version >= (4,4,0):
            slot_i = get_action_slot_idx(duplicate_armature.animation_data.action, duplicate_armature.animation_data.action_slot)
        
        fcurves = get_action_fcurves(duplicate_armature.animation_data.action, slot_idx=slot_i, as_list=True)

        for fc_index, fc in enumerate(fcurves):
            if not fc.data_path.startswith("pose.bones"):
                if "rotation" in fc.data_path or "location" in fc.data_path or "scale" in fc.data_path:
                    delete_fcurve(duplicate_armature.animation_data.action, fc)
                
    # Store bones X axis
    bpy.ops.object.mode_set(mode='EDIT')
    
    bones_x_axes = {}
    for eb in duplicate_armature.data.edit_bones:
        bones_x_axes[eb.name] = matrix_loc_rot(duplicate_armature.matrix_world) @ eb.x_axis.normalized()
    
    # Apply transforms    
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)    
    
    # Ensure bones roll is preserved, applying scale may break it
    bpy.ops.object.mode_set(mode='EDIT')
    
    for eb_name in bones_x_axes:
        saved_x_axis = bones_x_axes[eb_name]  
        eb = get_edit_bone(eb_name)
        align_bone_x_axis(eb, saved_x_axis)
    
    # Normalize the edit bones rest position (source armature only)
    if arm_type == "source":
        # centered
        # height above the origin
        bound_low = float(inf)
        bound_up = -float(inf)
        bound_right = -float(inf)
        bound_left = float(inf)
        bound_front = float(inf)
        bound_back = -float(inf)
        bones_data = {}
        
        #   get boundaries  
        for ebone in duplicate_armature.data.edit_bones:
            bones_data[ebone.name] = {"roll": ebone.roll}
            if ebone.head[0] > bound_right:
                bound_right = ebone.head[0]
            if ebone.head[0] < bound_left:
                bound_left = ebone.head[0]
            if ebone.head[1] > bound_back:
                bound_back = ebone.head[1]
            if ebone.head[1] < bound_front:
                bound_front = ebone.head[1]
            if ebone.head[2] < bound_low:
                bound_low = ebone.head[2]
            if ebone.head[2] > bound_up:
                bound_up = ebone.head[2]
                
        center_x = (bound_right + bound_left) / 2
        center_y = (bound_front + bound_back) / 2
        #bound_low -= (bound_up-bound_low)/20# add 5% offset from the ground
        
        #print("left", bound_left, "right", bound_right, "front", bound_front, "back", bound_back)
        for ebone in duplicate_armature.data.edit_bones:
            if ebone.use_connect:
                ebone.tail += -Vector((center_x, center_y, bound_low))
            else:
                ebone.head += -Vector((center_x, center_y, bound_low))
                ebone.tail += -Vector((center_x, center_y, bound_low))
            ebone.roll = bones_data[ebone.name]["roll"]# make sure to preserve roll
        
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # Bake
    if base_action_name:
        frame_range = duplicate_armature.animation_data.action.frame_range     
        bake_anim(frame_start=frame_range[0], frame_end=frame_range[1], only_selected=False, bake_bones=True, bake_object=False)

    # Delete constraints
    for pbone in duplicate_armature.pose.bones:
        for cns in pbone.constraints:
            if cns.name.startswith("arp_remap_temp"):
                pbone.constraints.remove(cns)

    # Delete old armature
    delete_object(get_object(base_arm_name))
    
    duplicate_armature.name = base_arm_name

    # Delete old actions    
    if base_action_name:
        bpy.data.actions.remove(bpy.data.actions.get(base_action_name), do_unlink=True)
        try:
            bpy.data.actions.remove(bpy.data.actions.get(base_action_name + "_TEMP_COPY"), do_unlink=True)
        except:
            pass

    # Rename new action
    if base_action_name:
        duplicate_armature.animation_data.action.name = base_action_name

    # restore frame
    scn.frame_set(saved_frame)    
    
    # restore loc       
    duplicate_armature.location = saved_loc
    
    # Assign back armature modifiers
    for obj_name in skinned_meshes:
        obj = get_object(obj_name)
        for mod in obj.modifiers:
            if mod.type != "ARMATURE":
                continue
            mod.object = duplicate_armature
    
    # restore parented meshes
    for obj_name in parented_meshes:
        obj = get_object(obj_name)
        obj_mat = obj.matrix_world.copy()
        obj.parent = duplicate_armature
        bpy.context.evaluated_depsgraph_get().update()
        obj.matrix_world = obj_mat

    # meshes object parented to bones support (no skinning): set new bones parent
    bpy.ops.object.mode_set(mode='POSE')
    
    for obj_name in meshes_parented_to_bones:
        obj = get_object(obj_name)
        mat = obj.matrix_world.copy()
        obj.parent = duplicate_armature
        obj.parent_type = "BONE"
        original_parent_name = meshes_parented_to_bones[obj_name]
        obj.parent_bone = original_parent_name
        # bone parent use_relative option must be enabled now
        duplicate_armature.data.bones.get(original_parent_name).use_relative_parent = True
        obj.matrix_world = mat

   
    #print("Armature is frozen.")
    

def _auto_scale(self, context):
    scene = context.scene
    source_rig = get_object(scene.source_rig)
    target_rig = get_object(scene.target_rig)
    #switch to rest pose
    source_rig.data.pose_position = 'REST'
    target_rig.data.pose_position = 'REST'
    #update hack
    bpy.context.scene.frame_set(bpy.context.scene.frame_current)

    def get_armature_dim(arm_obj):
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        set_active_object(arm_obj.name)
        bpy.ops.object.mode_set(mode='POSE')

        is_arp = False

        # Auto-Rig Pro armature case, exclude the picker bones if any
        if bpy.context.active_object.data.bones.get("Picker"):
            is_arp = True

        # get the source armature dimension
        highest = 0.0
        lowest = 100000000
        for bone in arm_obj.pose.bones:
            if is_arp:
                if bone.head[2] < 0:
                    continue

            z_head = (arm_obj.matrix_world @ bone.head)[2]
            z_tail = (arm_obj.matrix_world @ bone.tail)[2]

            if z_head > highest:
                highest = z_head
            if z_tail > highest:
                highest = z_tail
            if z_head < lowest:
                lowest = z_head
            if z_tail < lowest:
                lowest = z_tail


        dim = highest - lowest
        return dim


    source_dim = get_armature_dim(source_rig)
    #print("source dim", source_dim)
    target_dim = get_armature_dim(target_rig)
    #print("target dim", target_dim)

    fac = target_dim / source_dim
    
    # remove existing scale keyframes if any
    # animated scale of the source armature is not supported    
    if source_rig.animation_data:
        act = source_rig.animation_data.action
        if act:
            slot_i = 0
            if bpy.app.version >= (4,4,0):
                slot_i = get_action_slot_idx(act, source_rig.animation_data.action_slot)
            
            fcurves = get_action_fcurves(act, slot_idx=slot_i)
            for fc in fcurves:
                if fc.data_path == 'scale':
                    delete_fcurve(act, fc)
    
    source_rig.scale *= fac * 0.87

    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')

    #switch to pose position
    source_rig.data.pose_position = 'POSE'
    target_rig.data.pose_position = 'POSE'


def _clear_interactive_tweaks():
    print("Clearing interactive tweaks...")
    context = bpy.context
    scn = context.scene    
    source_rig = get_object(scn.source_rig)
    target_rig = get_object(scn.target_rig)
    if target_rig == None:
        return
        
    bind_mode = get_bind_state(target_rig)
       
    if bind_mode:
        for bone_item in scn.bones_map_v2:
            bone_name = bone_item.name
            
            # clear rot add
            remap_name = ''
            if bone_item.set_as_root:
                bone_name = bone_item.name
                remap_name = bone_name + '_REMAP'
            else:                
                bone_name = bone_item.source_bone
                remap_name = bone_name + '_REMAPTWEAK'
            bone_remap = source_rig.pose.bones.get(remap_name)        
            
            if bone_remap:
                bone_remap.rotation_euler = [0,0,0]
                #print("cleared", bone_remap.name)
            bone_item.rot_add_bind = Vector((0,0,0))   

            # clear loc add
            target_pb = target_rig.pose.bones.get(bone_name)
            if target_pb:
                #print("BONE NAME", bone_name)
                remap_name = ''
                for cns in target_pb.constraints:
                    if cns.name.endswith('_loc_REMAP'):
                        remap_name = cns.subtarget                    
                
            bone_remap = source_rig.pose.bones.get(remap_name)
            
            if bone_remap:  
                bone_remap.location = [0,0,0]
            bone_item.loc_add_bind = Vector((0,0,0))
            
            
    else:
        action = None
        if target_rig.animation_data:
            action = target_rig.animation_data.action            
        if action == None:
            return
        
        for bone_item in scn.bones_map_v2:
            bone_name = bone_item.name
            # clear rot add
            fac = bone_item.rot_add
            if fac != Vector((0,0,0)):
                for idx, add_value in enumerate(fac):
                    f = find_fcurve(action, 'pose.bones["'+bone_name+'"].rotation_euler', fc_index=idx)
                    if f:
                        for key in f.keyframe_points:
                            key.co[1] -= add_value
                            key.handle_left[1] -= add_value
                            key.handle_right[1] -= add_value
                            
            bone_item.rot_add = Vector((0,0,0))                    
                            
            # clear loc add
            fac = bone_item.loc_add
            if fac != Vector((0,0,0)):
                for idx, add_value in enumerate(fac):
                    f = find_fcurve(action, 'pose.bones["'+bone_name+'"].location', fc_index=idx)
                    if f:
                        for key in f.keyframe_points:
                            key.co[1] -= add_value
                            key.handle_left[1] -= add_value
                            key.handle_right[1] -= add_value
        
            bone_item.loc_add = Vector((0,0,0))          
        
        # clear loc mult
            fac = bone_item.loc_mult
            if fac != 0.0:           
                for idx in range(0, 3):                    
                    f = find_fcurve(action, 'pose.bones["'+bone_name+'"].location', fc_index=idx)
                    if f:
                        for key in f.keyframe_points:
                            key.co[1] *= 1/fac
                            key.handle_left[1] *= 1/fac
                            key.handle_right[1] *= 1/fac
                            
            bone_item.loc_mult = 1.0  
    
    print("Interactive tweaks cleared.")
    
    
def get_bind_state(target_rig):
    state = False
    if len(target_rig.keys()):
        if "arp_retarget_bound" in target_rig.keys():
            if target_rig["arp_retarget_bound"] == True:
                state = True
    
    return state
    
    
def _apply_offset(value, post_baking=False, set_selection=True, bind_mode=None):
   
    context = bpy.context
    scn = context.scene
    source_rig = get_object(scn.source_rig)
    target_rig = get_object(scn.target_rig)    
    
    if set_selection:# for performance optim
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        set_active_object(scn.target_rig)    
    
    if bind_mode == None:
        bind_mode = get_bind_state(target_rig)
    
    selected_bone_item = scn.bones_map_v2[scn.bones_map_index]

    # Apply  offset
    saved_loc_mult = False
    saved_loc_add = False
    saved_rot_add = False
    saved_rot_add_bind = False
    saved_loc_add_bind = False
    
    if "rot" in value:
        fac = scn.additive_rot
        if "-" in value:
            fac = -scn.additive_rot
        if post_baking:# after baking, use the saved value
            if bind_mode:
                fac = selected_bone_item.rot_add_bind
                #print("set rot_add_bind")
            else:
                fac = selected_bone_item.rot_add# Vector x, y, z: (0.5, 0.1, 1.2)
                #print("set set_rot_add")
    
    if "loc" in value and not "loc_mult" in value:
        fac = scn.additive_loc
        if "-" in value:
            fac = -scn.additive_loc
        if post_baking:
            if bind_mode:
                fac = selected_bone_item.loc_add_bind
            else:
                fac = selected_bone_item.loc_add
            
    if "loc_mult" in value:
        fac = scn.loc_mult
        if post_baking:
            if not bind_mode:
                fac = selected_bone_item.loc_mult
    
    if bind_mode:
        if 'rot' in value:
            remap_name = ''
            if scn.bones_map_v2[scn.bones_map_index].set_as_root:
                bone_name = scn.bones_map_v2[scn.bones_map_index].name
                remap_name = bone_name + '_REMAP'
            else:                
                bone_name = scn.bones_map_v2[scn.bones_map_index].source_bone
                remap_name = bone_name + '_REMAPTWEAK'
            bone_remap = source_rig.pose.bones.get(remap_name)
            
            if bone_remap:             
                bone_remap.rotation_mode = 'YXZ'                
                
                if post_baking:
                    bone_remap.rotation_euler = vectorize3(bone_remap.rotation_euler) + fac
                else:
                    rot_idx = 0 
                    if 'y' in value:
                        rot_idx = 1
                    elif 'z' in value:
                        rot_idx = 2
                        
                    bone_remap.rotation_euler[rot_idx] += fac
                    
                    # save it in bones_map data
                    if not saved_rot_add_bind:
                        if "x" in value:
                            add_vec = Vector((fac, 0, 0))
                        elif "y" in value:
                            add_vec = Vector((0, fac, 0))
                        elif "z" in value:
                            add_vec = Vector((0, 0, fac))
                        selected_bone_item.rot_add_bind += add_vec
                        saved_rot_add_bind = True
            
        if 'loc' in value and not 'loc_mult' in value:
            bone_name = scn.bones_map_v2[scn.bones_map_index].name
            target_pb = target_rig.pose.bones.get(bone_name)
            if target_pb:
                remap_name = ''
                for cns in target_pb.constraints:
                    if cns.name.endswith('_loc_REMAP') or cns.name.endswith(' LocationREMAP'):
                        remap_name = cns.subtarget                    
                    
                bone_remap = source_rig.pose.bones.get(remap_name)
                
                if bone_remap:   
                    if post_baking:
                        bone_remap.location += fac
                    else:
                        loc_idx = 0 
                        if 'y' in value:
                            loc_idx = 1
                        elif 'z' in value:
                            loc_idx = 2
                            
                        bone_remap.location[loc_idx] += fac
                        
                        # save it in bones_map data
                        if not saved_loc_add_bind:
                            if "x" in value:
                                add_vec = Vector((fac, 0, 0))
                            elif "y" in value:
                                add_vec = Vector((0, fac, 0))
                            elif "z" in value:
                                add_vec = Vector((0, 0, fac))
                            selected_bone_item.loc_add_bind += add_vec
                            saved_loc_add_bind = True
        
    else:
        action = None 
        if target_rig.animation_data:
            action = target_rig.animation_data.action         
        if action == None:
            return

        fcurves = get_action_fcurves(action, as_list=True)
        
        for f in fcurves:
            bone_name = (f.data_path.split('"')[1])
            # Rotation
            if "rot" in value and not post_baking:# after baking, rather use direct fcurves access for convenience
                if 'rotation' in f.data_path:                    
                    try:
                        if bone_name == scn.bones_map_v2[scn.bones_map_index].name:                       
                            if (f.array_index == 0 and "x" in value) or (f.array_index == 1 and "y" in value) or (f.array_index == 2 and "z" in value):      
                                for key in f.keyframe_points:
                                    key.co[1] += fac
                                    key.handle_left[1] += fac
                                    key.handle_right[1] += fac
                                        
                            # save it in bones_map_v2 data
                            if not saved_rot_add:
                                if "x" in value:
                                    add_vec = Vector((fac, 0, 0))
                                elif "y" in value:
                                    add_vec = Vector((0, fac, 0))
                                elif "z" in value:
                                    add_vec = Vector((0, 0, fac))
                                selected_bone_item.rot_add += add_vec
                                saved_rot_add = True
                    except:
                        pass

            # Location
            if "loc" in value and not "loc_mult" in value and not post_baking:# after baking, rather use direct fcurves access for convenience
                if 'location' in f.data_path:# location curves only
                    try:
                        if bone_name == scn.bones_map_v2[scn.bones_map_index].name:
                            if (f.array_index == 0 and "x" in value) or (f.array_index == 1 and "y" in value) or (f.array_index == 2 and "z" in value):                     
                                for key in f.keyframe_points:
                                    key.co[1] += fac
                                    key.handle_left[1] += fac
                                    key.handle_right[1] += fac  
                            
                            # save it in bones_map_v2 data
                            if not saved_loc_add:
                                if "x" in value:
                                    add_vec = Vector((fac, 0, 0))
                                elif "y" in value:
                                    add_vec = Vector((0, fac, 0))
                                elif "z" in value:
                                    add_vec = Vector((0, 0, fac))
                                selected_bone_item.loc_add += add_vec
                                saved_loc_add = True                           
                    except:
                        pass

            # Loc Multiply
            if "loc_mult" in value:
                if 'location' in f.data_path:
                    try:
                        if bone_name == selected_bone_item.name: 
                            if f.array_index == 0 or f.array_index == 1 or f.array_index == 2:
                                for key in f.keyframe_points:
                                    key.co[1] *= fac

                            # save it in bones_map_v2 data
                            if not post_baking and not saved_loc_mult:
                                selected_bone_item.loc_mult *= scn.loc_mult
                                saved_loc_mult = True
                    except:
                        pass
        
        
        if post_baking:# set fcurves for additive location and rotation post-baking here
            if value == "rot_add":
                
                for idx, add_value in enumerate(fac):
                    f = find_fcurve(action, 'pose.bones["'+selected_bone_item.name+'"].rotation_euler', fc_index=idx)
                    if f:
                        for key in f.keyframe_points:
                            key.co[1] += add_value
                            key.handle_left[1] += add_value
                            key.handle_right[1] += add_value
            
            elif value == "loc_add":
                for idx, add_value in enumerate(fac):
                    f = find_fcurve(action, 'pose.bones["'+selected_bone_item.name+'"].location', fc_index=idx)
                    if f:
                        for key in f.keyframe_points:
                            key.co[1] += add_value
                            key.handle_left[1] += add_value
                            key.handle_right[1] += add_value

    
    #update hack
    bpy.ops.object.mode_set(mode='OBJECT')
    #current_frame = scn.frame_current#save current frame
    scn.frame_set(scn.frame_current)


def _cancel_redefine():
    scn = bpy.context.scene
    source_rig = get_object(scn.source_rig)
    target_rig = get_object(scn.target_rig)
    preserve = source_rig["remap_redefine_preserve"]
    
    if preserve:
        source_rig.data.pose_position = 'POSE'
        source_action_name, source_action_slot = get_source_action_name(get_slot=True)
        assign_armature_action(source_rig, bpy.data.actions.get(source_action_name), _slot_idx=source_action_slot)
        target_rig.data.pose_position = 'POSE'
        
    else:
        source_rig_copy = get_object(scn.source_rig+'_copy')
        source_rig.data.pose_position = 'POSE'
        
        slotidx = 0
        if bpy.app.version >= (4,4,0):
            slotidx = get_action_slot_idx(source_rig_copy.animation_data.action, source_rig_copy.animation_data.action_slot)
        
        assign_armature_action(source_rig, source_rig_copy.animation_data.action, _slot_idx=slotidx)
        
        delete_object(source_rig_copy)
        
        target_rig.data.pose_position = 'POSE'
        
        # update hack
        scn.frame_set(scn.frame_current)
        
    del source_rig["remap_redefine_rest_pose"]
    
    
def _redefine_rest_pose(self, context):
    scn = context.scene
    source_rig = get_object(scn.source_rig)
    target_rig = get_object(scn.target_rig)
    
    if source_rig.animation_data.action != None and get_source_action_name() != source_rig.animation_data.action.name:# not ideal but in case it has been changed meanwhile
        save_source_action(source_rig)      
        
    source_rig['remap_redefine_preserve'] = self.preserve
    
    # ensure the source armature selection
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    set_active_object(scn.source_rig)
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # if current pose is used, save bone transforms
    current_pose_mat = {}
    if self.rest_pose == 'CURRENT':
        bpy.ops.object.mode_set(mode='POSE')
        for pbone in source_rig.pose.bones:
            current_pose_mat[pbone.name] = pbone.matrix.copy()
            
        bpy.ops.object.mode_set(mode='OBJECT')
        
    # set the target in rest pose for correct transform copy
    target_rig.data.pose_position = 'REST'
    
    

    if self.preserve:# preserve the actual rest pose, only take a snapshot of it
        # reset transforms
        bpy.ops.object.mode_set(mode='POSE')
        
        source_rig.animation_data.action = None    
        
        mat_basis_dict = None
        if 'rest_transf_offset' in scn.keys():           
            mat_basis_dict = scn['rest_transf_offset']
        
        for pbone in source_rig.pose.bones:
            if self.rest_pose == 'REST':
                pbone.location = [0,0,0]
                pbone.rotation_euler = [0,0,0]
                pbone.rotation_quaternion = [1,0,0,0]
                pbone.scale = [1,1,1]     
                
            elif self.rest_pose == 'CURRENT':
                pbone.matrix = current_pose_mat[pbone.name]
                
            elif self.rest_pose == 'SAVED':
                found = False
                if mat_basis_dict:
                    if pbone.name in mat_basis_dict:
                        found = True
                        
                if found:
                        pbone.location, rot_mode_foo , pbone.rotation_euler, pbone.rotation_quaternion = mat_basis_dict[pbone.name]
                else:
                    pbone.location = [0,0,0]
                    pbone.rotation_euler = [0,0,0]
                    pbone.rotation_quaternion = [1,0,0,0]
                    pbone.scale = [1,1,1]     
        
        bpy.ops.pose.select_all(action='DESELECT')
        
    else:# do not preserve the rest pose, apply it
        # duplicate the skeleton as a reference
        bpy.ops.object.duplicate_move(OBJECT_OT_duplicate={"linked":False, "mode":'TRANSLATION'}, TRANSFORM_OT_translate={"value":(0, 0, 0), "constraint_axis":(False, True, False), "mirror":False, "snap":False, "remove_on_cancel":False, "release_confirm":False})    
       
        armature_copy = bpy.data.objects.get(bpy.context.active_object.name)
        
        # rename
        armature_copy.name = scn.source_rig+'_copy'
        if armature_copy.animation_data.action != None:
            armature_copy.animation_data.action.name = get_source_action_name()+'_COPY'
        
        # hide it
        hide_object(armature_copy)
        
        bpy.ops.object.select_all(action='DESELECT')
        set_active_object(scn.source_rig)
        
        # reset transforms
        bpy.ops.object.mode_set(mode='POSE')        
        
        source_rig.animation_data.action = None
        
        
        for pbone in source_rig.pose.bones:
            if self.rest_pose == 'REST':
                reset_pbone_transforms(pbone)                
                
            elif self.rest_pose == 'CURRENT':
                pbone.matrix = current_pose_mat[pbone.name]
        
        bpy.ops.pose.select_all(action='DESELECT')
        
    # tag the source rig for edition
    source_rig['remap_redefine_rest_pose'] = 1        
    
    
def _apply_pose_as_rest(rig):
    # 1.Apply armature modifiers of meshes
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')

    shape_keys_objects = []
    skinned_objects_dict = {}
            
    for obj in bpy.data.objects:
        if len(obj.modifiers) == 0 or obj.type != 'MESH' or is_object_hidden(obj):
            continue
        for modindex, mod in enumerate(obj.modifiers):
            if mod.type != 'ARMATURE':
                continue
            if mod.object != rig or mod.object == None:
                continue

            # save the armature modifiers to restore them later
            if obj.name not in skinned_objects_dict:
                skinned_objects_dict[obj.name] = {}
            if mod.object:  # safety check
                skinned_objects_dict[obj.name][mod.name] = [mod.object.name, mod.use_deform_preserve_volume,
                                                            mod.use_multi_modifier, modindex]

            # objects with shape keys are handled separately, since modifiers can't be applied here
            if obj.data.shape_keys:
                if not obj in shape_keys_objects:                  
                    shape_keys_objects.append(obj)
                continue

            # apply modifier         
            set_active_object(obj.name)
            if mod.show_viewport:
                apply_modifier(mod.name)               
   
    # handle objects with shape keys
    for obj_sk in shape_keys_objects:    
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        
        # duplicate the mesh
        dupli_mesh = duplicate_object(method='data', obj=obj_sk)      

        # delete shape keys on the original mesh
        set_active_object(obj_sk.name)
        for i in reversed(range(len(obj_sk.data.shape_keys.key_blocks))):
            obj_sk.active_shape_key_index = i
            bpy.ops.object.shape_key_remove()

        # apply modifiers
        for mod in obj_sk.modifiers:
            if mod.type != 'ARMATURE': continue
            if mod.use_multi_modifier:# do not apply if "multi modifier" is enabled, incorrect result... skip for now
                obj_sk.modifiers.remove(mod)
                continue
            if mod.object == rig:
                set_active_object(obj_sk.name)
                apply_modifier(mod.name)

        # transfer shape keys
        transfer_shape_keys_deformed(dupli_mesh, obj_sk)

        # delete duplicate
        if dupli_mesh:
            bpy.data.objects.remove(dupli_mesh, do_unlink=True)

    # Restore modifiers
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')

    for obj_name in skinned_objects_dict:
        set_active_object(obj_name)
        _obj = bpy.data.objects[obj_name]
        for mod_name in skinned_objects_dict[obj_name]:
            
            new_mod = _obj.modifiers.new(type="ARMATURE", name=mod_name)
            arm_name = skinned_objects_dict[obj_name][mod_name][0]
            preserve_bool = skinned_objects_dict[obj_name][mod_name][1]
            use_multi = skinned_objects_dict[obj_name][mod_name][2]
            new_mod.object = bpy.data.objects[arm_name]
            new_mod.use_deform_preserve_volume = preserve_bool
            new_mod.use_multi_modifier = use_multi

        def get_current_mod_index(mod_name):
            mod_dict = {}
            for i, mod in enumerate(bpy.context.active_object.modifiers):
                mod_dict[mod.name] = i
            return mod_dict[mod_name]

        # re-order the modifiers stack
        for mod_name in skinned_objects_dict[obj_name]:
            target_index = skinned_objects_dict[obj_name][mod_name][3]
            current_index = get_current_mod_index(mod_name)
            move_delta = current_index - target_index
            if move_delta == 0:
                continue
            for i in range(0, abs(move_delta)):
                if move_delta < 0:
                    bpy.ops.object.modifier_move_down(modifier=mod_name)
                else:
                    bpy.ops.object.modifier_move_up(modifier=mod_name)

    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    set_active_object(rig.name)
    bpy.ops.object.mode_set(mode='POSE')   
    bpy.ops.pose.armature_apply(selected=False)


def _save_pose_rest(self):
    scn = bpy.context.scene
    mat_basis_dict = {}
    source_rig = get_object(scn.source_rig)
    target_rig = get_object(scn.target_rig)
    
    set_active_object(scn.source_rig)
    
    bpy.ops.object.mode_set(mode='POSE')
    
    for b in source_rig.pose.bones:
        mat_basis_dict[b.name] = [b.location.copy(), b.rotation_mode, b.rotation_euler.copy(), b.rotation_quaternion.copy()]
    
    scn['rest_transf_offset'] = mat_basis_dict
    
    # link back action
    source_action_name, source_action_slot = get_source_action_name(get_slot=True)
    assign_armature_action(source_rig, bpy.data.actions.get(source_action_name), _slot_idx=source_action_slot)
    
    target_rig.data.pose_position = 'POSE'
    
    del source_rig["remap_redefine_rest_pose"]
    

def _copy_raw_coordinates(self, context):
    scn = bpy.context.scene
    get_object(scn.target_rig).data.pose_position = 'POSE'
    source_rig = get_object(scn.source_rig)    
    
    source_rig_copy = get_object(scn.source_rig+'_copy')
    unhide_object(source_rig_copy)
    
    # Ensure the source armature is selected
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    set_active_object(scn.source_rig)
    bpy.ops.object.mode_set(mode='POSE')
    
    # Apply as rest pose    
    _apply_pose_as_rest(source_rig)
    
    source_rig_copy.location = source_rig.location.copy()
    
    # setup constraints
    for bone in source_rig.pose.bones:
        cns = bone.constraints.new('COPY_TRANSFORMS')
        cns.name = 'arp_redefine'
        cns.target = source_rig_copy
        cns.subtarget = bone.name

    actions_list = {}
    armatures_actions_save = {}# save actions-armature links of all armature if any and restore them at the end of the process
    first_act_slot = 0
    first_act_name = ''
    
    if scn.batch_retarget:
        for act in bpy.data.actions:
            if 'arp_remap' in act.keys() and act['arp_remap'] == True:
                slot_i = 0# multi slots not supported for now, except for the active action of the source armature
                if first_act_name == '':
                    first_act_name = act.name
                    
                if act == source_rig_copy.animation_data.action:
                    first_act_name = act.name
                    
                    if bpy.app.version >= (4,4,0):
                        slot_i = get_action_slot_idx(act, source_rig_copy.animation_data.action_slot)
                        first_act_slot = slot_i                        
                        
                actions_list[act.name] = slot_i
                
                # save actions-armature links of all armature if any and restore them at the end of the process
                if not act.name.endswith('_COPY'):
                    for obj in bpy.data.objects:
                        if obj.type == 'ARMATURE':
                            if obj.animation_data and obj.animation_data.action:
                                if obj.animation_data.action == act:
                                    armatures_actions_save[obj.name] = act.name
                                    
    else:
        first_act_name = source_rig_copy.animation_data.action.name        
        if bpy.app.version >= (4,4,0):
            first_act_slot = get_action_slot_idx(source_rig_copy.animation_data.action, source_rig_copy.animation_data.action_slot)
            #print('first_act_slot', first_act_slot)
            
        actions_list[first_act_name] = first_act_slot
        
    if first_act_name.endswith('_COPY'):
        first_act_name = first_act_name[:-5]
        
    current_frame = scn.frame_current#save current frame
    
    # bake
    for actname in actions_list:    
        _action = bpy.data.actions.get(actname)
        _slot = actions_list[actname]
        assign_armature_action(source_rig_copy, _action, _slot_idx=_slot)
        
        print("bake...")   
        bake_anim(frame_start=_action.frame_range[0], frame_end=_action.frame_range[1], only_selected=False, bake_bones=True, bake_object=False)
        
        # remove original action
        bpy.data.actions.remove(_action)
        
        # rename new action
        source_rig.animation_data.action.name = actname
        
        # enable fake user
        source_rig.animation_data.action.use_fake_user = True

        
    # delete constraints
    print("delete constraints...")
    for bone in source_rig.pose.bones:
        for cns in bone.constraints:
            if cns.name == 'arp_redefine':
                bone.constraints.remove(cns)
    
    # restore current frame   
    scn.frame_set(current_frame)
    
    delete_object(source_rig_copy)
    del source_rig["remap_redefine_rest_pose"]

    # update source anim
    save_source_action(source_rig)
    
    # restore other armature actions (multiple anims)
    for arm_name in armatures_actions_save:
        other_arm = get_object(arm_name)
        act_name = armatures_actions_save[arm_name]
        assign_armature_action(other_arm, bpy.data.actions.get(act_name))
    
    print("Redefining done.")
    

def bonesmap_source_items(self, context):
    # make a list of the names
    items = []

    if context is None:
        return items

    i = 1
    names_string = context.scene.source_nodes_name_string
    if names_string != '':
        for name in names_string.split('+'):
            items.append((name, name, name, i))
            i += 1
    else:
        items.append(('None', 'None', 'None'))

    return items
    
    
def find_closest_match(word, word_list, threshold=0.6):
    closest_match = None
    closest_match_ratio = 0
    valid_match = None
    
    while valid_match == None and threshold > 0.3:
        for candidate in word_list:
            ratio = difflib.SequenceMatcher(None, word, candidate).ratio()
            if ratio > closest_match_ratio:
                closest_match_ratio = ratio
                closest_match = candidate
      
        if closest_match_ratio >= threshold:
            valid_match = closest_match
        else:
            threshold -= 0.1
        
    return valid_match
    
    
def _mirror_bones_list(mirror_dir):

    scn = bpy.context.scene
    tar_rig = get_object(scn.target_rig)
    src_rig = get_object(scn.source_rig)
    
    sides_dict = {'l': 'r', 'left': 'right'}
    
    if mirror_dir == "RIGHT_TO_LEFT":
        reverse_dict = {}
        for i in sides_dict:
            reverse_dict[sides_dict[i]] = i
            
        sides_dict = reverse_dict
    
    
    def get_mirror_side(side_word):
        mirror_word = None
        
        for dict_word in sides_dict:
            if dict_word == side_word:
                mirror_word = sides_dict[dict_word]
            if dict_word.upper() == side_word:# upper case
                mirror_word = sides_dict[dict_word].upper()
            if dict_word.title() == side_word:# capital first
                mirror_word = sides_dict[dict_word].title()
                
        return mirror_word
        
        
    def get_mirror_name_nested(val, sides_dict, check_list=[]):
        # eg mixamorig:RFoot
        for _si in sides_dict:           
            if _si in val.lower():
                for side_id in [_si, _si.upper(), _si.title()]:# look for lower, upper and title format
                    if side_id in val:
                        count = val.count(side_id)
                        split = val.split(side_id)
                        mirror_word = get_mirror_side(side_id)
                        
                        for spliti in range(1, count+1):                            
                            mirror_src_name = side_id.join(split[:spliti]) + mirror_word + side_id.join(split[spliti:])                            
                            # mirror bone found?
                            if mirror_src_name in check_list:
                                #print(mirror_src_name)
                                return mirror_src_name                            
         
        return ''
    
        
    def get_mirror_name(name, check_list=[]):
        mirror_src_name = ''
        # is there a side id?
        for sep in ['.', '_', ' ','-']:            
            split = name.split(sep)
                
            # side suffix
            suff = split[len(split)-1]#.l, .r, _left ...            
           
            mirror_word = get_mirror_side(suff)

            if mirror_word:
                mirror_src_name = name[:-len(suff)]+mirror_word   
                break
                
            # prefix
            pref = split[0]#l., r., right_
            mirror_word = get_mirror_side(pref)
            if mirror_word:
                mirror_src_name = mirror_word + name[len(pref):]
                break            

            # inside
            for wordi, word in enumerate(split):#thigh right twist
                mirror_word = get_mirror_side(word)
                if mirror_word:
                    mirror_src_name = ''
                    for _i, _word in enumerate(split):
                        mirror_src_name += _word if _i != wordi else mirror_word
                        if _i != len(split)-1:
                            mirror_src_name += sep
        
        
        if mirror_src_name == '':# nested side id? eg mixamorig:RightFoot
            mirror_src_name = get_mirror_name_nested(name, sides_dict, check_list=check_list)
            
        return mirror_src_name
        
    
    mirrorable_source_bones = {}
    
    # look for bones to mirror
    for item in scn.bones_map_v2:
        src_name = item.source_bone
        mirror_src_name = get_mirror_name(src_name, check_list=[b.name for b in src_rig.data.bones])
        
        # target bone is not found, skip
        tar_bone = tar_rig.data.bones.get(item.name)
        if tar_bone == None:
            continue
            
        # mirrored name not found, skip
        if src_rig.data.bones.get(mirror_src_name) == None:
            continue
        
        # side id found, look for mirror target
        if mirror_src_name != '':       
            mirror_target_name = get_mirror_name(item.name, check_list=[b.name for b in tar_rig.data.bones])
         
            if mirror_target_name != '':
                tar_mirror_bone = tar_rig.data.bones.get(mirror_target_name)
                if tar_mirror_bone:
                    settings_dict = {'name': mirror_target_name}                   
                    # copy other settings
                    for prop in dir(item):
                        val = getattr(item, prop)
                        if prop in ['name', 'source_bone', 'bl_rna', 'rna_type', 'id', 'set_as_root'] or prop.startswith('__'):# cannot set set_as_root, it deactivates other settings...
                            continue
                        if prop in ['rot_add', 'loc_add', 'loc_mult', 'rot_add_bind', 'loc_add_bind']:# exclude interactive tweaks
                            continue
                            
                        # mirror the IK pole name
                        if prop == 'ik_pole':
                            pole_name_mirror = get_mirror_name(val)
                            if tar_rig.data.bones.get(pole_name_mirror):
                                val = pole_name_mirror
                        
                        settings_dict[prop] = val
                            
                    mirrorable_source_bones[mirror_src_name] = settings_dict
    
    # assign mirrors
    for mirror_src_name in mirrorable_source_bones:   
        for item2 in scn.bones_map_v2:
            if item2.source_bone != mirror_src_name:
                continue
                
            settings_dict = mirrorable_source_bones[mirror_src_name]
    
            for prop in settings_dict:
                val = settings_dict[prop]
                setattr(item2, prop, val)
           
            break
            

def _build_bones_list():
    sides_dict = {'l': 'r', 'left': 'right'}
    reverse_dict = {}
    for i in sides_dict:
        reverse_dict[sides_dict[i]] = i
    sides_dict.update(reverse_dict)

    def get_mirror_side(side_word):
        mirror_word = None
        
        for dict_word in sides_dict:
            if dict_word == side_word:
                mirror_word = sides_dict[dict_word]
            if dict_word.upper() == side_word:# upper case
                mirror_word = sides_dict[dict_word].upper()
            if dict_word.title() == side_word:# capital first
                mirror_word = sides_dict[dict_word].title()
                
        return mirror_word
        
        
    def is_excluded_ctrl(ctrl_name):
        exclude_non_ctrl_sw = ['c_p_', 'c_foot_bank_']
            
        exclude_non_ctrl = ['c_foot_fk_scale_fix', 'c_hand_fk_scale_fix', 'c_foot_roll', 'c_foot_heel', 'c_toes_track', 'c_toes_end', 'c_toes_end_01',
             'c_thumb1_rot', 'c_thumb2_rot', 'c_thumb3_rot',
            'c_index1_rot', 'c_index2_rot', 'c_index3_rot',
            'c_middle1_rot', 'c_middle2_rot', 'c_middle3_rot',
            'c_ring1_rot', 'c_ring2_rot', 'c_ring3_rot',
            'c_pinky1_rot', 'c_pinky2_rot', 'c_pinky3_rot']
            
        for non_ctrl_name in exclude_non_ctrl_sw:
            if ctrl_name.startswith(non_ctrl_name):
                return True
        
        for non_ctrl_name in exclude_non_ctrl:
            if get_bone_base_name(ctrl_name) == non_ctrl_name:
                return True
        
        return False

        
    scn = bpy.context.scene    
    
    bpy.ops.object.select_all(action='DESELECT')
    
    #select the target rig
    set_active_object(scn.target_rig)

    target_pose_bones = get_object(scn.target_rig).pose.bones
    is_arp_armature = target_pose_bones.get("c_traj") and target_pose_bones.get("c_pos")    
    src_rig = get_object(scn.source_rig)
    is_src_arp_armature = src_rig.data.bones.get("c_traj") and src_rig.data.bones.get("c_pos")
    
    # clear current list
    if len(scn.bones_map_v2):
        i = len(scn.bones_map_v2)
        while i >= 0:
            scn.bones_map_v2.remove(i)
            i -= 1

    # Get source action bone names
    if len(scn.remap_source_nodes):
        i = len(scn.remap_source_nodes)
        while i >= 0:
            scn.remap_source_nodes.remove(i)
            i -= 1
    
    for b in src_rig.data.bones:
        if is_src_arp_armature:
            if is_excluded_ctrl(b.name):
                continue
        item = scn.remap_source_nodes.add()
        item.source_name = b.name
    
    # create the collection items, one per source bone
    sources_nodes_list = [i.source_name for i in scn.remap_source_nodes]
    sources_nodes_list.sort()# we want it in alphabetical order
    
    for i in sources_nodes_list:
        item = scn.bones_map_v2.add()
        item.name = 'None'
        item.source_bone = i

    pose_bones_list = []
    
                    
    for b in target_pose_bones:
        if is_arp_armature:
            if b.name.startswith("c_") or "cc" in b.keys():# must be a bone controller or custom controller
                
                # exclude specials, not controllers
                if is_excluded_ctrl(b.name):
                    continue                    
              
                pose_bones_list.append(b.name)
        else:
            pose_bones_list.append(b.name)

    # Guess linked bones, try to find Auto-Rig Pro bones match, if not lambda name match
    # side aware
    
    assigned_bones = []# helper list to avoid duplicates

    for item in scn.bones_map_v2:
        found = False
        name_low = item.source_bone.lower()

        # ARP specials
        # exclude non controller source bones
        if is_src_arp_armature:            
            if not item.source_bone.startswith("c_") or is_excluded_ctrl(item.source_bone):
                continue

        def get_side(str):
            if 'left' in str or " l " in str or "_l_" in str or "lft" in str or ".l" in str or "-l" in str or str.endswith('_l') or str.startswith('l_'):
                return ".l"
                
            elif 'right' in str or " r " in str or "_r_" in str or "rgt" in str or ".r" in str or "-r" in str or str.endswith('_r') or str.startswith('r_'):
                return ".r"
                
            return None
            
        def set_target_name(bname):
            if bname in assigned_bones:# already assigned, skip
                item.name = ''
                return False
            else:
                if target_pose_bones.get(bname):
                    item.name = bname   
                    assigned_bones.append(bname)
                    return True

        # head
        if 'head' in name_low:
            found = set_target_name("c_head.x")
            
        # neck
        if 'neck' in name_low:
            found = set_target_name("c_neck.x")
          
        # spine 01
        if 'abdomen' in name_low or 'spine' in name_low:
            found = set_target_name("c_spine_01.x")
          
        # spine 02
        if 'chest' in name_low or 'spine2' in name_low:
            found = set_target_name("c_spine_02.x")
          
        # root master
        if 'hip' in name_low:
            found = set_target_name("c_root_master.x")
            if found:
                item.set_as_root = True         

        if 'tospine' in name_low:
            if target_pose_bones.get("c_root_master.x"):
                item.name = 'None'
                item.set_as_root = True
                found = True

        if 'pelvis' in name_low:
            found = set_target_name("c_root_master.x")
            if found:
                item.set_as_root = True

        # shoulder
        if 'collar' in name_low or "shoulder" in name_low or "clavicle" in name_low:
            side = get_side(name_low)
            if side:
                found = set_target_name("c_shoulder"+side)               

        # arm
        #   special cases
        if 'rshldr' in name_low or ('right' in name_low and 'arm' in name_low and not 'fore' in name_low):
            found = set_target_name("c_arm_fk.r")

        if 'lshldr' in name_low or ('left' in name_low and 'arm' in name_low and not 'fore' in name_low):
            found = set_target_name("c_arm_fk.l")

        #   more common
        if "upperarm" in name_low:
            side = get_side(name_low)
            if side:
                found = set_target_name("c_arm_fk"+side)

        # forearms
        #   special cases
        if 'rforearm' in name_low or ('right' in name_low and 'forearm' in name_low):
            found = set_target_name("c_forearm_fk.r")
        elif 'lforearm' in name_low or ('left' in name_low and 'forearm' in name_low):
            found = set_target_name("c_forearm_fk.l")
        #   more common
        elif "forearm" in name_low:
            side = get_side(name_low)
            if side:
                found = set_target_name("c_forearm_fk"+side)

        # hand
        if 'hand' in name_low:
            side = get_side(name_low)
            if side:
                found = set_target_name("c_hand_fk"+side)               

        # thigh
        if 'lthigh' in name_low:
            found = set_target_name("c_thigh_fk.l")

        if 'rthigh' in name_low:
            found = set_target_name("c_thigh_fk.r")

        if 'upleg' in name_low or 'thigh' in name_low:
            side = get_side(name_low)
            if side:
                found = set_target_name("c_thigh_fk"+side)

        # calf
        if 'lshin' in name_low:
            found = set_target_name("c_leg_fk.l")

        if 'rshin' in name_low:
            found = set_target_name("c_leg_fk.r")

        if ('leg' in name_low and not "upleg" in name_low) or 'shin' in name_low or "calf" in name_low:
            side = get_side(name_low)            
            if side:
                found = set_target_name("c_leg_fk"+side)

        # foot
        if 'foot' in name_low:
            side = get_side(name_low)
            if side:
                found = set_target_name("c_foot_fk"+side)

        # toes
        if 'toe' in name_low or 'ball' in name_low:
            side = get_side(name_low)
            if side:
                found = set_target_name("c_toes_fk"+side)              


        finger_list = ['thumb', 'index', 'middle', 'ring', 'pinky']
        for fing in finger_list:
            for side in ['l', 'r']:
                for fing_idx in ['1', '2', '3']:
                    full_side = ""
                    if side == 'l':
                        full_side = 'left'
                    if side == 'r':
                        full_side = 'right'

                    # look for lThumb1 or LeftThumb1 or Thumb1_l or Thumb1_left or LeftHandThumb1
                    item_name = item.source_bone.lower()
                    if (fing+fing_idx+'_'+side) in item_name or (side+fing+fing_idx) in item_name or (full_side in item_name and fing+fing_idx in item_name):
                        found = set_target_name('c_'+fing+fing_idx+'.'+side)
                        

        if not found:
            # Fuzzy match if not found
            #print("Could not find automatically, try fuzzy match:", item.source_bone)
            
            try:                
                #closest_match = difflib.get_close_matches(item.source_bone, pose_bones_list)[0]                
                closest_match = find_closest_match(item.source_bone, pose_bones_list, threshold=0.5)
                
                if closest_match:
                    #print("result", closest_match)
                    set_target_name(closest_match)
                    
                    # try to ensure sides match
                    sides_match = True
                    # any sides found?
                    if get_side(item.name.lower()) and get_side(item.source_bone.lower()):
                        # are sides identical?
                        if get_side(item.name.lower()) != get_side(item.source_bone.lower()):
                            sides_match = False
                    
                    
                    if not sides_match:                
                        #print("Sides don't match:", item.name, item.source_bone)
                        val = item.name
                        
                        # No side separators
                        side_sep = True
                        side_dict = {"Left":"Right", "left":"right",
                                     "Right":"Left", "right":"left"}
                        for k in side_dict:
                            if k in val:
                                val = val.replace(k, side_dict[k])
                                side_sep = False     
                                break
                             
                        # With side separators: ., _, space
                        if side_sep:
                            for sep in ['.', '_', ' ']:
                                split = val.split(sep)
                                
                                if len(split) == 0:
                                    continue
                                    
                                # side suffix
                                suff = split[len(split)-1]#.l, .r, _left ...
                                
                                mirror_word = get_mirror_side(suff)
                                if mirror_word:
                                    val = val[:-len(suff)]+mirror_word            
                                    break
                                    
                                # prefix
                                pref = split[0]#l., r., right_
                                mirror_word = get_mirror_side(pref)
                                if mirror_word:
                                    val = mirror_word + val[len(pref):]
                                    break            

                                # inside
                                for wordi, word in enumerate(split):#thigh right twist
                                    mirror_word = get_mirror_side(word)
                                    if mirror_word:
                                        val = ''
                                        for _i, _word in enumerate(split):
                                            val += _word if _i != wordi else mirror_word
                                            if _i != len(split)-1:
                                                val += sep
                        
                        set_target_name(val)
                            
            except:
                pass

    scn.bones_map_index = 0


def _retarget(self):
    print("\nRetargetting...")
    
    context = bpy.context
    scn = context.scene    
    source_rig = get_object(scn.source_rig)
    target_rig = get_object(scn.target_rig)
    
    def set_ik_fk_switch_remap(keyframe=False, keyframe_only=False):
        for bone_item in scn.bones_map_v2:
            target_bone = get_pose_bone(bone_item.name)
            if target_bone:
                if target_bone.name.startswith('c_foot_ik') or target_bone.name.startswith('c_hand_ik'):
                    if 'ik_fk_switch' in target_bone.keys():
                        if not keyframe_only:
                            target_bone['ik_fk_switch'] = 0.0
                        if keyframe:
                            target_bone.keyframe_insert(data_path='["ik_fk_switch"]', frame=1)
                elif target_bone.name.startswith('c_foot_fk') or target_bone.name.startswith('c_hand_fk'):
                    ik_pbone = get_pose_bone(target_bone.name.replace('fk', 'ik'))
                    if ik_pbone:
                        if 'ik_fk_switch' in ik_pbone.keys():
                            if not keyframe_only:
                                ik_pbone['ik_fk_switch'] = 1.0
                            if keyframe:
                                ik_pbone.keyframe_insert(data_path='["ik_fk_switch"]', frame=1)
                            
                            
    def set_fingers_to_fk(keyframe=False, keyframe_only=False):
        for side in ['.l', '.r']:
            for fingername in ard.fingers_control:
                #print('fingername', fingername+side)
                finger_pb = get_pose_bone(fingername+side)
                if finger_pb:
                    #print("Found finger")
                    if 'ik_fk_switch' in finger_pb.keys():
                        if not keyframe_only:
                            finger_pb['ik_fk_switch'] = 1.0
                        if keyframe:
                            finger_pb.keyframe_insert(data_path='["ik_fk_switch"]', frame=1)
                        #print("Set finger to FK", finger_pb.name)
                        

    preserve = False
    if 'remap_redefine_preserve' in source_rig.keys() and 'rest_transf_offset' in scn.keys():
        preserve = source_rig['remap_redefine_preserve']    
    

    # make sure the target armature is visible
    armature_hidden = is_object_hidden(target_rig)
    unhide_object(target_rig)
    current_frame = scn.frame_current#save current frame

    # Handle proxy or override target armatures
    target_proxy_name = None  
    
    if is_proxy(target_rig):
        target_proxy_name = target_rig.proxy.name
        print("  The target armature is a proxy. Real name = ", target_proxy_name)
        
    overridden_armature = False
    
    if target_rig.override_library:
        overridden_armature = True
        print('  Overridden armature')
    
    #   duplicate
    local_armature_name = scn.target_rig+'_local'
    if target_proxy_name or overridden_armature:
        if get_object(local_armature_name) == None:
            duplicate_object(method='data', obj=get_object(scn.target_rig), new_name=local_armature_name)
    
    #   select target
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    set_active_object(scn.target_rig)
    
    # unlink current action and reset pose
    bpy.ops.object.mode_set(mode='POSE')
    
    anim_data = target_rig.animation_data
    if anim_data:
        if anim_data.action:
            anim_data.action = None
    
    try:
        bpy.ops.arp.reset_pose()
        set_ik_fk_switch_remap()
        set_fingers_to_fk()
    except:
        pass

    # is it already bound?
    is_already_bound = False
    if len(target_rig.keys()):
        if "arp_retarget_bound" in target_rig.keys():
            if target_rig["arp_retarget_bound"] == True:
                is_already_bound = True
    
    if is_already_bound == False and self.unbind == False:
        print("  Binding...")
        
        # save the bound state in a property
        target_rig["arp_retarget_bound"] = True

        bpy.ops.object.mode_set(mode='POSE')

        # set source armature at target armature position
        source_armature_init_pos = source_rig.location.copy()
        source_rig.location = target_rig.location.copy()

        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')        
        
        # Localize proxy or overridden armatures
        local_armature_name = scn.target_rig + "_local"
        
        if target_proxy_name == None and overridden_armature == False:
            set_active_object(scn.target_rig)
        elif target_proxy_name:
            print("  Localize proxy...")
            set_active_object(local_armature_name)
            proxy_armature = get_object(local_armature_name)
            proxy_armature.data = proxy_armature.data.copy()
        elif overridden_armature:
            print("  Localize override...")            
            set_active_object(local_armature_name)
            proxy_armature = get_object(local_armature_name)
            proxy_armature.data = proxy_armature.data.copy()
            bpy.ops.object.make_local(type='SELECT_OBDATA')#(type='SELECT_OBJECT')  
            
            
        target_mat_rest = {}
        mat_rest_diff = {}
        mat_redef_rest = {}

        if preserve:        
            # get target bones matrices in rest pose
            bpy.ops.object.mode_set(mode='POSE')
            
            #   zero out pose     
            anim_data = target_rig.animation_data
            if anim_data:
                if anim_data.action:
                    anim_data.action = None                    
            
            for pb_tar in target_rig.pose.bones:
                reset_pbone_transforms(pb_tar)    
                
            scn.frame_set(scn.frame_current)# bones transforms update hack
            
            for pb_tar in target_rig.pose.bones:
                target_mat_rest[pb_tar.name] = target_rig.matrix_world @ pb_tar.matrix
            
            target_rig.data.pose_position = 'POSE'
            
            # compute diff with source bones matrices in redefined rest pose
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')           
            set_active_object(scn.source_rig)
            bpy.ops.object.mode_set(mode='POSE')            
            
            if source_rig.animation_data.action:
                save_source_action(source_rig)# update current scene action, may have been changed
            
            #   zero out pose
            source_rig.animation_data.action = None
            
            #   set redefined rest pose
            transf_offset_dict = scn['rest_transf_offset']          
            
            for bname in transf_offset_dict.keys():
                pb_src = get_pose_bone(bname)
                if pb_src == None:
                    print("Warning,", bname, "is None! The source armature has been edited (bone addition, renaming...), retargetting is prone to error")
                    mat_redef_rest[bname] = Matrix()
                    continue
                    
                pb_src.location, pb_src.rotation_mode, pb_src.rotation_euler, pb_src.rotation_quaternion = transf_offset_dict[bname]
                pb_src.scale = [1.0, 1.0, 1.0]# for now, only normalized scale is supported
                scn.frame_set(scn.frame_current)# bones transforms update hack
                mat_redef_rest[bname] = pb_src.matrix.copy()
            
            #   get diff
            for pb_src in source_rig.pose.bones:
                target_name = get_target_bone_name(pb_src.name)
                if target_name:
                    if target_name in target_mat_rest:
                        mat_rest_diff[pb_src.name] = pb_src.matrix.inverted() @ source_rig.matrix_world.inverted() @ target_mat_rest[target_name]
                    

            #   restore action
            source_act_name, source_slot = get_source_action_name(get_slot=True)
            assign_armature_action(source_rig, bpy.data.actions.get(source_act_name), _slot_idx=source_slot)
            
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            
            if target_proxy_name or overridden_armature:
                set_active_object(local_armature_name)
            else:
                set_active_object(scn.target_rig)
          
        local_tar_rig = context.active_object        
        
        for pb_tar in target_rig.pose.bones:
            reset_pbone_transforms(pb_tar)    
                
        bpy.ops.object.mode_set(mode='EDIT')

        # create a transform dict of target bones
        tar_bones_dict = {}        
        obj_mat = local_tar_rig.matrix_world
        
        for edit_bone in local_tar_rig.data.edit_bones:
            tar_bones_dict[edit_bone.name] = {
                'matrix': obj_mat @ edit_bone.matrix,
                'head': obj_mat @ edit_bone.head, 
                'tail': obj_mat @ edit_bone.tail, 
                'roll': mat3_to_vec_roll(obj_mat.to_3x3() @ edit_bone.matrix.to_3x3()),
                'x_axis': (obj_mat @ edit_bone.x_axis.normalized()).normalized()
                }

        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        set_active_object(scn.source_rig)
        bpy.ops.object.mode_set(mode='EDIT')
        
        # display layer 24 / collection remap01
        if bpy.app.version >= (4,0,0):
            collec_remap01 = get_armature_collections(source_rig).get('remap01')
            if collec_remap01 == None:
                collec_remap01 = source_rig.data.collections.new('remap01')
            collec_remap01.is_visible = True
        else:
            source_rig.data.layers[24] = True
        
        obj_mat = source_rig.matrix_world.inverted()
        
        print("  Creating Bones...")
        
        #autorot_constraints = True
        ik_chains = {}
        fk_chains = []
        loc_helper_bones = []
        
        
        # create the _tweak skeleton for Interactive Tweaks (Bind)
        tweak_suffix = '_REMAPTWEAK'
        
        bone_names = [b.name for b in source_rig.data.edit_bones]
        for bname in bone_names:
            eb = get_edit_bone(bname)            
            tweak_b = create_edit_bone(eb.name+tweak_suffix)
            tweak_b['arp_remap_temp_bone'] = 1# tag it for deletion
            copy_bone_transforms(eb, tweak_b)    
            tweak_b.use_inherit_rotation = eb.use_inherit_rotation
            set_bone_layer(tweak_b, 'remap02')
            
        #   parent
        for eb in source_rig.data.edit_bones:
            if is_bone_in_layer(eb.name, 'remap02'):     
                if eb.name.endswith(tweak_suffix):
                    source_par = get_edit_bone(eb.name[:-len(tweak_suffix)])
                    par = source_par.parent
                    if par:                        
                        eb.parent = get_edit_bone(par.name+tweak_suffix)
        
        #   constrain
        bpy.ops.object.mode_set(mode='POSE')
        
        for pb in source_rig.pose.bones:
            if is_bone_in_layer(pb.name, 'remap02'):         
                if pb.name.endswith(tweak_suffix):                  
                    cns = pb.constraints.new('COPY_TRANSFORMS')
                    cns.target = source_rig
                    cns.subtarget = pb.name[:-len(tweak_suffix)]
                    cns.owner_space = cns.target_space = 'LOCAL'
                    cns.mix_mode = 'BEFORE'
                    
        bpy.ops.object.mode_set(mode='EDIT')
        
        # create bones
        idxi = 0
        for bone_item in scn.bones_map_v2:
            idxi += 1 
            
            source_bone_name = bone_item.source_bone
            eb_source_bone = get_edit_bone(source_bone_name)          
        
            if bone_item.name != "" and bone_item.name != "None" and eb_source_bone and bone_item.name in tar_bones_dict:            
                # main
                bone_remap = create_edit_bone(bone_item.name+"_REMAP")                
                bone_remap['arp_remap_temp_bone'] = 1# tag it for deletion
                if preserve:
                    # copy target bones transforms for length
                    bone_remap.head, bone_remap.tail = obj_mat @ tar_bones_dict[bone_item.name]['head'], obj_mat @ tar_bones_dict[bone_item.name]['tail']                 
                    bone_remap.length = eb_source_bone.length / source_rig.scale[0]
                    
                    # apply mat diff of redefined rest pose                    
                    if eb_source_bone.name in mat_rest_diff:
                        mat_offset = eb_source_bone.matrix @ mat_rest_diff[eb_source_bone.name]
                        # only use loc rot, scale is buggy if the armature has scale != 1                                       
                        bone_remap.matrix = matrix_loc_rot(mat_offset)
                    else:
                        print("Missing in mat_rest_diff", eb_source_bone.name)
                    
                    # keep it on source bone position
                    offset_vec = eb_source_bone.head - bone_remap.head                    
                    bone_remap.head += offset_vec
                    bone_remap.tail += offset_vec
                    
                    # scale bone length (for visual only)
                    bone_remap.tail = bone_remap.head + (bone_remap.tail-bone_remap.head) * ((source_rig.scale[0] + source_rig.scale[1] + source_rig.scale[2])/3)
                    
                else:
                    # copy target bones transforms
                    bone_remap.matrix = obj_mat @ tar_bones_dict[bone_item.name]['matrix']
                    bone_remap.head, bone_remap.tail = obj_mat @ tar_bones_dict[bone_item.name]['head'], obj_mat @ tar_bones_dict[bone_item.name]['tail']
                    #align_bone_x_axis(bone_remap, obj_mat @ tar_bones_dict[bone_item.name]['x_axis'])                
               
                bone_remap.parent = get_edit_bone(eb_source_bone.name+tweak_suffix)
                set_bone_layer(bone_remap, 'remap01') 

                
                # set as root
                if bone_item.set_as_root:
                    # root offset
                    root_offset_name = bone_item.name+"_ROOT_OFFSET"
                    root_offset = create_edit_bone(root_offset_name) 
                    root_offset['arp_remap_temp_bone'] = 1# tag it for deletion
                    copy_bone_transforms(eb_source_bone, root_offset)
                    set_bone_layer(root_offset, 'remap01')
                    
                    # root pos
                    root_pos_name = bone_item.name+"_ROOT"
                    root_pos = create_edit_bone(root_pos_name)    
                    root_pos['arp_remap_temp_bone'] = 1# tag it for deletion
                    root_pos.matrix = obj_mat @ tar_bones_dict[bone_item.name]['matrix']
                    root_pos.head, root_pos.tail = obj_mat @ tar_bones_dict[bone_item.name]['head'], obj_mat@ tar_bones_dict[bone_item.name]['tail']
                    root_pos.length = eb_source_bone.length                    
                
                    if preserve:
                        # apply redefine rest pose offset
                        root_offset_vec = eb_source_bone.head - mat_redef_rest[source_bone_name].to_translation()
                        root_pos.head += root_offset_vec
                        root_pos.tail += root_offset_vec
                          
                    
                    #align_bone_x_axis(root_pos, tar_bones_dict[bone_item.name]['x_axis'])  
                    root_pos.parent = root_offset
                    set_bone_layer(root_pos, 'remap01')
                    
                    bpy.ops.object.mode_set(mode='POSE')

                    # add location constraint
                    bone_root_offset_pb = source_rig.pose.bones.get(root_offset_name)
                    cns = bone_root_offset_pb.constraints.new('COPY_LOCATION')
                    cns.target = source_rig
                    cns.subtarget = source_bone_name
                    cns.name += 'REMAP'
                    
                    bpy.ops.object.mode_set(mode='EDIT')
                    
                # optional: location
                if bone_item.location:
                   
                    eb_source_bone = get_edit_bone(source_bone_name)
                    bone_remap_loc_name = bone_item.name+"_LOC"
                    bone_remap_loc = create_edit_bone(bone_remap_loc_name)
                    bone_remap_loc['arp_remap_temp_bone'] = 1# tag it for deletion
                    set_bone_layer(bone_remap_loc, 'remap01')
                    
                    bone_remap = get_edit_bone(bone_item.name+"_REMAP")    
                    
                    if eb_source_bone.parent:
                        copy_bone_transforms(bone_remap, bone_remap_loc)
                    else:
                        bone_remap_loc.matrix = obj_mat @ tar_bones_dict[bone_item.name]['matrix']
                        bone_remap_loc.head, bone_remap_loc.tail = obj_mat @ tar_bones_dict[bone_item.name]['head'], obj_mat @ tar_bones_dict[bone_item.name]['tail']
                    offset_vec = eb_source_bone.head - bone_remap_loc.head
                    bone_remap_loc.head += offset_vec
                    bone_remap_loc.tail += offset_vec
                            
                    bone_remap_loc.parent = eb_source_bone.parent

                    bpy.ops.object.mode_set(mode='POSE')

                    # add location constraint
                    bone_remap_loc_pb = get_pose_bone(bone_remap_loc_name)
                    cns = bone_remap_loc_pb.constraints.new('COPY_LOCATION')
                    cns.target = source_rig
                    cns.subtarget = source_bone_name
                    cns.name += 'REMAP'

                    bpy.ops.object.mode_set(mode='EDIT')
                
                # optional: ik bones
                if bone_item.ik:
                    eb_source_bone = get_edit_bone(source_bone_name)
                    
                    # add ik helper offset bone
                    ikloc_off_name = bone_item.name+"_IKLOC_offset"
                    ikloc_off = create_edit_bone(ikloc_off_name)
                    ikloc_off['arp_remap_temp_bone'] = 1# tag it for deletion
                    copy_bone_transforms(eb_source_bone, ikloc_off)                    
                    set_bone_layer(ikloc_off, 'remap01')
                    
                    # add an IK helper bone
                    ikloc_name = bone_item.name+"_IKLOC"
                    ik_loc = create_edit_bone(ikloc_name)
                    ik_loc['arp_remap_temp_bone'] = 1# tag it for deletion
                    
                    if bone_item.ik_world:
                        copy_bone_transforms(eb_source_bone, ik_loc)      
                    else:
                        ik_loc.matrix = obj_mat @ tar_bones_dict[bone_item.name]['matrix']
                        ik_loc.head, ik_loc.tail = obj_mat @ tar_bones_dict[bone_item.name]['head'], tar_bones_dict[bone_item.name]['tail']
                    
                    ik_loc.length = ikloc_off.length   
                    ik_loc.parent = ikloc_off
                    
                    if preserve:
                        ik_offset_vec = eb_source_bone.head - mat_redef_rest[source_bone_name].to_translation()
                        ik_loc.head += ik_offset_vec
                        ik_loc.tail += ik_offset_vec                        
                    
                    set_bone_layer(ik_loc, 'remap01')
                    #loc_helper_bones.append(ikloc_name)                 
                    
                    
                    # constraint
                    bpy.ops.object.mode_set(mode='POSE')   
                    
                    ikloc_off = get_pose_bone(ikloc_off_name)    
                    cns = ikloc_off.constraints.new('COPY_LOCATION')
                    cns.target = source_rig
                    cns.subtarget = source_bone_name           
                    cns.influence = 1.0
                    cns.name += 'REMAP'
                  
                    bpy.ops.object.mode_set(mode='EDIT')
                    
                    eb_source_bone = get_edit_bone(source_bone_name)
                    
                    if bone_item.ik_pole != "":
                        bone_parent_1 = eb_source_bone.parent if bone_item.ik_2 == '' else get_edit_bone(bone_item.ik_2)

                        # check for missing bones
                        if bone_parent_1 == None:
                            print("Can't setup IK, incorrect bones hierarchy")
                            continue# the IK hierarchy is incorrect, the target IK bone has no parent, skip it

                        bone_parent_2 = bone_parent_1.parent if bone_item.ik_1 == '' else get_edit_bone(bone_item.ik_1)

                        if bone_parent_2 == None:
                            print("Can't setup IK, incorrect bones hierarchy")
                            continue# the IK hierarchy is incorrect, the IK chain is made of bone only instead of 2, skip it

                        bone_parent_1_name = bone_parent_1.name
                        bone_parent_2_name = bone_parent_2.name

                        # track bone
                        track_bone_name = bone_item.name+"_IK_REMAP"
                        track_bone = create_edit_bone(track_bone_name)
                        track_bone['arp_remap_temp_bone'] = 1# tag it for deletion
                        set_bone_layer(track_bone, 'remap01')
                        
                        
                        # Check for ik chains straight alignment
                        # No ideal way to correct a straight chain, since the direction is unknown
                        # give it a try though :)
                        method = 2
                        if method == 1:
                            # bone axis vector evaluation, may be incorrect
                            if bone_parent_1.y_axis.angle(bone_parent_2.y_axis) == 0.0:
                                print("  Warning: Straight IK chain (" + bone_item.name + "), adding offset...")
                                # find foot direction if any
                                bone_vec = None
                                for ed_bone in source_rig.data.edit_bones:
                                    if 'foot' in ed_bone.name.lower():
                                        print("    found a foot bone as reference for offset")
                                        bone_vec = ed_bone.tail - ed_bone.head
                                        break
                                        
                                # else, get the current bone vector... not the good way to find the elbow direction :-(
                                if bone_vec == None:
                                    bone_vec = eb_source_bone.tail - eb_source_bone.head

                                if 'hand' in bone_item.name.lower():
                                    bone_vec *= -1
                            
                                #offset the middle position
                                x_axis1, x_axis2 = bone_parent_1.x_axis.copy(), bone_parent_2.x_axis.copy()# make sure to preserve roll, may get corrupted
                                bone_parent_1.head += bone_vec/5
                                bone_parent_2.tail += bone_vec/5
                                align_bone_x_axis(bone_parent_1, x_axis1)
                                align_bone_x_axis(bone_parent_2, x_axis2)
                        
                        
                        elif method == 2:
                            print("  Warning: Straight IK chain (" + bone_item.name + "), adding offset...", bone_item.IK_axis_correc)
                            # actual bone position evaluation
                            vec1 = (bone_parent_2.head - bone_parent_1.head)
                            vec2 = (bone_parent_1.head - eb_source_bone.head)
                            angle = degrees(vec1.angle(vec2))
                            x_axis1, x_axis2 = bone_parent_1.x_axis.copy(), bone_parent_2.x_axis.copy()# make sure to preserve roll, may be changed when altering transforms
                       
                            fac = -1 if '-' in bone_item.IK_axis_correc else 1
                            vec_dir = Vector((fac*0.01,0,0)) 
                            if 'Y' in bone_item.IK_axis_correc:
                                vec_dir = Vector((0,fac*0.01,0))
                            elif 'Z' in bone_item.IK_axis_correc:
                                vec_dir = Vector((0,0,fac*0.01))
                            
                            vec = vec_dir @ source_rig.matrix_world
                            # or get the foot axis if any
                            if 'foot' in eb_source_bone.name:
                                vec = (eb_source_bone.y_axis)/10
                            
                            t = 0
                            while angle < 0.1 and t < 2000:    
                                t += 1
                                # then try on X
                                if t > 500:
                                    vec = Vector((0.01, 0.0, 0.0)) @ source_rig.matrix_world
                                # then Z
                                elif t > 1000:
                                    vec = Vector((0.0, 0.0, 0.1)) @ source_rig.matrix_world
                                    
                                bone_parent_1.head += vec
                                vec1 = (bone_parent_2.head - bone_parent_1.head)
                                vec2 = (bone_parent_1.head - eb_source_bone.head)
                                angle = degrees(vec1.angle(vec2))
                                
                            if t >= 2000:
                                print("Failed to correct IK chain angle!")                            
                            
                            align_bone_x_axis(bone_parent_1, x_axis1)
                            align_bone_x_axis(bone_parent_2, x_axis2)
                        
                        # track_bone coords
                        #   mid point evaluation, not best
                        #track_bone.head = (eb_source_bone.head + bone_parent_2.head) * 0.5
                        #   direct line projection evaluation, best                        
                        track_bone.head = project_point_onto_line(bone_parent_2.head, eb_source_bone.head, bone_parent_1.head)
                        track_bone.tail = bone_parent_1.head.copy()
                        
                        d1 = (track_bone.tail - bone_parent_2.head).magnitude
                        
                        d_tot = (eb_source_bone.head - bone_parent_2.head).magnitude
                        ik_chains[source_bone_name] = [bone_parent_1_name, bone_parent_2_name, bone_item.ik_pole]
                        
                        # FK pole
                        fk_pole_name = bone_item.name+"_FK_POLE_REMAP"
                        fk_pole = create_edit_bone(fk_pole_name)
                        fk_pole['arp_remap_temp_bone'] = 1# tag for deletion
                        set_bone_layer(fk_pole, 'remap01')                        
                        
                        eb_source_bone = get_edit_bone(source_bone_name)
                        
                        if bone_item.ik_auto_pole == 'RELATIVE_TARGET':
                            # keep the current IK pole target coords
                            fk_pole.matrix = obj_mat @ tar_bones_dict[bone_item.ik_pole]['matrix']
                            fk_pole.head, fk_pole.tail = obj_mat @ tar_bones_dict[bone_item.ik_pole]['head'], obj_mat @ tar_bones_dict[bone_item.ik_pole]['tail']
                            
                            if preserve:    
                                # apply mat
                                if eb_source_bone.name in mat_redef_rest:
                                    mat_diff = eb_source_bone.matrix @ mat_redef_rest[eb_source_bone.name].inverted()
                                    # only use loc rot. Scale is buggy if the armature has scale != 1   
                                    fk_pole.matrix = matrix_loc_rot(mat_diff) @ fk_pole.matrix
                                else: print("Missing in mat_rest_diff", eb_source_bone.name)
                            
                            # just parent the FK pole to the foot/hand...
                            fk_pole.parent = eb_source_bone
                            
                        elif bone_item.ik_auto_pole == 'ABSOLUTE':
                            # otherwise parent to the track bone to evaluate the true IK pole vector
                            fk_pole.head = track_bone.tail + (track_bone.tail-track_bone.head).normalized() * ((bone_parent_1.tail-bone_parent_1.head).magnitude + (bone_parent_2.tail-bone_parent_2.head).magnitude)                      
                            fk_pole.tail = fk_pole.head + (track_bone.tail - track_bone.head)*2
                            fk_pole.parent = track_bone
                            
                        elif bone_item.ik_auto_pole == 'RELATIVE_CHAIN':
                            # keep the current IK pole target coords                          
                            fk_pole.matrix = obj_mat @ tar_bones_dict[bone_item.ik_pole]['matrix']
                            fk_pole.head, fk_pole.tail = obj_mat @ tar_bones_dict[bone_item.ik_pole]['head'], obj_mat @ tar_bones_dict[bone_item.ik_pole]['tail']
                            
                            if preserve:    
                                # apply mat
                                if eb_source_bone.name in mat_redef_rest:
                                    mat_diff = eb_source_bone.matrix @ mat_redef_rest[eb_source_bone.name].inverted()
                                    # only use loc rot. Scale is buggy if the armature has scale != 1   
                                    fk_pole.matrix = matrix_loc_rot(mat_diff) @ fk_pole.matrix
                                else: print("Missing in mat_rest_diff", eb_source_bone.name)
                            
                            fk_pole.parent = bone_parent_2
                        
                        
                        # Add constraints
                        bpy.ops.object.mode_set(mode='POSE')
                        
                        p_track_bone = get_pose_bone(track_bone_name)
                        if p_track_bone == None:# bone deleted because of null coordinates, due to invalid IK chain. Skip
                            print("Can't setup IK, incorrect bones hierarchy")
                            continue
                            
                        cns = p_track_bone.constraints.new('COPY_LOCATION')
                        cns.target = context.active_object
                        cns.subtarget = bone_parent_2_name
                        cns.name += 'REMAP'
                        
                        cns = p_track_bone.constraints.new('COPY_LOCATION')
                        cns.target = context.active_object
                        cns.subtarget = source_bone_name
                        #cns.head_tail = 1.0
                        cns.influence = d1/d_tot#0.5
                        cns.name += 'REMAP'
                        
                        cns = p_track_bone.constraints.new('TRACK_TO')
                        cns.target = context.active_object
                        cns.subtarget = bone_parent_1_name
                        cns.influence = 1.0
                        cns.name += 'REMAP'
                        cns.track_axis = "TRACK_Y"
                        cns.up_axis = "UP_Z"
                        
                # collect FK chains
                if bone_item.name.startswith('c_hand_fk') or bone_item.name.startswith('c_foot_fk'):
                    fk_chains.append(bone_item.name)
                
                bpy.ops.object.mode_set(mode='EDIT')    
                
        
        bpy.ops.object.mode_set(mode='POSE')
        
        print("  IK Chains:", ik_chains)
        # store in a prop for access later
        target_rig["arp_retarget_ik_chains"] = ik_chains
        
        print("  FK Chains:", fk_chains)
        # store in a prop for access later
        target_rig["arp_retarget_fk_chains"] = fk_chains
        

        print("  Add constraints...")
        # Add constraints
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        set_active_object(scn.target_rig)
        
        # set IK-FK switch of ARP armature automatically if found
        bpy.ops.object.mode_set(mode='POSE')
        
        set_ik_fk_switch_remap()
                            
        bpy.ops.object.mode_set(mode='OBJECT')

        # Add IK constraints if necessary
        for bone_item in scn.bones_map_v2:
            if bone_item.ik_create_constraints:
                bpy.ops.object.mode_set(mode='EDIT')
                eb_target_bone = get_edit_bone(bone_item.name)
                bone_parent = eb_target_bone.parent

                if bone_parent == None:
                    continue# the foot has no parent, we can't setup an IK chain

                bone_parent_parent = bone_parent.parent

                if bone_parent_parent == None:
                    continue# the calf has no parent, we can't setup an IK chain

                parent_name = bone_parent.name

                # unparent the IK foot/hand
                eb_target_bone.parent = None

                # create ik constraints
                bpy.ops.object.mode_set(mode='POSE')
                
                second_ik_bone = get_pose_bone(parent_name)
                ik_cns = second_ik_bone.constraints.get("IK")
                if ik_cns == None:
                    ik_cns = second_ik_bone.constraints.new("IK")

                ik_cns.target = bpy.context.active_object
                ik_cns.subtarget = bone_item.name
                ik_cns.chain_count = 2

        bpy.ops.object.mode_set(mode='POSE')
        bpy.ops.pose.select_all(action='DESELECT')


        for bone_item in scn.bones_map_v2:
            if bone_item.name != "" and bone_item.name != "None" and context.active_object.pose.bones.get(bone_item.name):
                
                pose_bone = context.active_object.pose.bones[bone_item.name]              
                context.active_object.data.bones.active = pose_bone.bone
                
                # Add constraints
                # main rotation
                cns = pose_bone.constraints.new('COPY_ROTATION')
                cns.target = source_rig
                cns.subtarget = bone_item.name + "_REMAP"
                cns.name += 'REMAP'

                # optional location
                if bone_item.location:
                    cns_loc = pose_bone.constraints.new('TRANSFORM')
                    cns_loc.target = source_rig
                    cns_loc.subtarget = bone_item.name + "_LOC"
                    cns_loc.name += '_loc_REMAP'
                    cns_loc.owner_space = cns_loc.target_space = 'LOCAL'
                    cns_loc.from_max_x = cns_loc.from_max_y = cns_loc.from_max_z = 1.0
                    cns_loc.to_max_x = cns_loc.to_max_y = cns_loc.to_max_z = source_rig.scale[0]
                    cns_loc.use_motion_extrapolate = True                  
                    
                if bone_item.set_as_root:
                    cns_root = pose_bone.constraints.new('COPY_LOCATION')
                    cns_root.target = source_rig
                    cns_root.subtarget = bone_item.name + "_ROOT"
                    cns_root.name += '_loc_REMAP'                 
                    cns_root.owner_space = cns_root.target_space = 'WORLD'

                # IKs
                if bone_item.ik:
                    cns = pose_bone.constraints.new('COPY_LOCATION')
                    cns.target = source_rig
                   
                    if bone_item.ik:
                        cns.subtarget = bone_item.name + "_IKLOC"
                        
                    cns.name += 'REMAP'

                    if bone_item.ik_pole != "":
                        pole = context.object.pose.bones[bone_item.ik_pole]
                        cns = pole.constraints.new('COPY_LOCATION')
                        cns.target = source_rig
                        cns.subtarget = bone_item.name+"_FK_POLE_REMAP"
                        cns.name += 'REMAP'
                        context.object.data.bones.active = context.object.pose.bones[bone_item.ik_pole].bone

                        if "pole_parent" in pole.keys():
                            pole['pole_parent'] = 0

        bpy.ops.object.mode_set(mode='OBJECT')
        
        # Apply saved Interactive Tweaks (bind mode)       
        print("  Apply interactive tweaks (bind mode)...")
        current_map_idx = scn.bones_map_index
        for idx in range(0, len(scn.bones_map_v2)):
            scn.bones_map_index = idx
            bone_item = scn.bones_map_v2[idx]
            
            # rot add
            if bone_item.rot_add_bind != Vector((0.0, 0.0, 0.0)):
                _apply_offset("rot_add", set_selection=False, post_baking=True)
            
            # loc add
            if bone_item.loc_add_bind != Vector((0.0, 0.0, 0.0)):
                _apply_offset("loc_add", set_selection=False, post_baking=True)            
        
    else:
        if self.unbind == False:
            print("Already bound")
            self.report({'INFO'}, "Already bound")

    if self.bind_only == False:
        
        # select baked bones
        for bone_item in scn.bones_map_v2:
            if bone_item.name != '' and bone_item.name != 'None' and context.active_object.pose.bones.get(bone_item.name):                
                pose_bone = context.active_object.pose.bones[bone_item.name]
                if bpy.app.version >= (5,0,0):
                    pose_bone.select = True
                else:
                    context.active_object.data.bones.active = pose_bone.bone
                
                if bone_item.ik_pole != '' and bone_item.ik:
                    pose_bone = context.active_object.pose.bones[bone_item.ik_pole]
                    if bpy.app.version >= (5,0,0):
                        pose_bone.select = True
                    else:
                        context.active_object.data.bones.active = pose_bone.bone
        
        slot_idx = 0
        if bpy.app.version >= (4,4,0):
            slot_idx = get_action_slot_idx(source_rig.animation_data.action, source_rig.animation_data.action_slot)
        
        actions_to_bake = {source_rig.animation_data.action.name: slot_idx}
        source_rig_original_action_name = source_rig.animation_data.action.name
        source_rig_original_slot = slot_idx
        
        if scn.batch_retarget:
            actions_to_bake = {}
            
            for act in bpy.data.actions:
            
                if scn.arp_remap_only_containing != '':# filter only containing
                    if not scn.arp_remap_only_containing in act.name:
                        continue
                    
                if 'arp_remap' in act.keys():
                    if act['arp_remap'] == True:
                        if not act.name in actions_to_bake:
                            slot_idx = 0
                            # only support the first slot for now when baking multiple actions, since they are not necessarily linked to an armature, no way to get the active slot
                            # TODO: add slot selection support in the multiple anims menu
                            if act.name == source_rig.animation_data.action.name and bpy.app.version >= (4,4,0):
                                slot_idx = get_action_slot_idx(source_rig.animation_data.action, source_rig.animation_data.action_slot)
                            
                            actions_to_bake[act.name] = slot_idx
                            
        frame_range = [self.frame_start, self.frame_end]

        for act_name in actions_to_bake:
            act_slot = actions_to_bake[act_name]
            # set source action
            assign_armature_action(source_rig, bpy.data.actions.get(act_name), _slot_idx=act_slot)
                
            #   zero out pose     
            anim_data = target_rig.animation_data
            if anim_data:
                if anim_data.action:
                    anim_data.action = None                    
            
            for pb_tar in target_rig.pose.bones:
                reset_pbone_transforms(pb_tar)
            
            existing_keyframes = {}
            
            if self.only_existing_keyframes:# collect keyframed frames
                for bone_item in scn.bones_map_v2:
                    target_name = bone_item.name
                    src_name = bone_item.source_bone                    
                    existing_keyframes[target_name] = get_bone_keyframes_list(None, bpy.data.actions.get(act_name), all_rot_modes=True, bonename=src_name)
            
            frstart = frame_range[0]
            frend = frame_range[1]
            
            if scn.batch_retarget:
                frstart = source_rig.animation_data.action.frame_range[0]
                frend = source_rig.animation_data.action.frame_range[1]
            
            print("\n  Baking action:", act_name, " [", int(frstart),"-", int(frend), "]")            
            
            bpy.ops.transform.rotate(value=0)# update hack

            # bake anim
            bake_anim(frame_start=frstart, frame_end=frend, only_selected=True, bake_bones=True, bake_object=False, 
                interpolation_type=self.interpolation_type, handle_type=self.handle_type, support_constraints=True, keyframes_dict=existing_keyframes)
            
            # keyframe IK-FK switches
            set_ik_fk_switch_remap(keyframe=True, keyframe_only=True)
            
            # Change action name
            target_rig.animation_data.action.name = source_rig.animation_data.action.name + '_remap'
            
            # should not be remappable
            target_rig.animation_data.action['arp_remap'] = False
            
            # copy cyclic settings
            for prop in ['use_frame_range', 'frame_start', 'frame_end', 'use_cyclic']:
                if prop in dir(source_rig.animation_data.action):# not part of earlier Blender versions
                    val = getattr(source_rig.animation_data.action, prop)
                    setattr(target_rig.animation_data.action, prop, val)
            
            # set fake user
            if self.fake_user_action or scn.batch_retarget:
                target_rig.animation_data.action.use_fake_user = True

            # Apply saved Interactive Tweaks:        
            print("  Apply interactive tweaks...")
            current_map_idx = scn.bones_map_index
            for idx in range(0, len(scn.bones_map_v2)):
                scn.bones_map_index = idx
                bone_item = scn.bones_map_v2[idx]
                
                # rot add
                if bone_item.rot_add != Vector((0.0, 0.0, 0.0)):
                    _apply_offset("rot_add", post_baking=True, bind_mode=False)
                
                # loc add
                if bone_item.loc_add != Vector((0.0, 0.0, 0.0)):
                    _apply_offset("loc_add", post_baking=True, bind_mode=False)
                
                # loc mult
                if bone_item.loc_mult != 1.0:
                    _apply_offset("loc_mult", post_baking=True, bind_mode=False)
                
            # restore bones list index
            scn.bones_map_index = current_map_idx
            
            fk_chains = None
            if 'arp_retarget_fk_chains' in target_rig.keys():
                fk_chains = target_rig["arp_retarget_fk_chains"]
                    
            # clean FK rotations
            if self.clean_fk_rot and fk_chains:
                
                #print('FK CHAINS:', fk_chains)
                #print(bpy.context.active_object.name)
                #print(bpy.context.mode)
                
                bpy.ops.object.mode_set(mode='POSE')
                
                for c_fk_name in fk_chains:
                    print('Clean FK Rotations:', c_fk_name, 'side', get_bone_side(c_fk_name), '...')
                    if 'hand' in c_fk_name:
                        # bake to IK
                        bpy.ops.pose.arp_bake_arm_ik_to_fk('EXEC_DEFAULT', get_sel_side=False, side=get_bone_side(c_fk_name), 
                                                            frame_start=int(frstart), frame_end=int(frend), multi_select=False)
                        # clear forearm FK keys
                        for i in range(0, 3):
                            fc = find_fcurve(target_rig.animation_data.action, 'pose.bones["'+c_fk_name.replace('hand', 'forearm')+'"].rotation_euler', fc_index=i)
                            if fc:
                                clear_fcurve(fc)
                                
                        # bake back to FK
                        bpy.ops.pose.arp_bake_arm_fk_to_ik('EXEC_DEFAULT', get_sel_side=False, side=get_bone_side(c_fk_name), 
                                                            frame_start=int(frstart), frame_end=int(frend), multi_select=False)
                    elif 'foot' in c_fk_name:
                        # bake to IK
                        bpy.ops.pose.arp_bake_leg_ik_to_fk('EXEC_DEFAULT', get_sel_side=False, side=get_bone_side(c_fk_name), 
                                                            frame_start=frstart, frame_end=frend, multi_select=False)
                                                            
                        # clear leg FK keys
                        for i in range(0, 3):
                            fc = find_fcurve(target_rig.animation_data.action, 'pose.bones["'+c_fk_name.replace('foot', 'leg')+'"].rotation_euler', fc_index=i)
                            if fc:
                                clear_fcurve(fc)
                                
                        # bake back to FK
                        bpy.ops.pose.arp_bake_leg_fk_to_ik('EXEC_DEFAULT', get_sel_side=False, side=get_bone_side(c_fk_name), 
                                                            frame_start=frstart, frame_end=frend, multi_select=False)
                    
                
                bpy.ops.object.mode_set(mode='OBJECT')
            
            
            if self.extract_root_motion:                
                bpy.ops.arp.extract_root_motion(loc_x=self.loc_x, loc_y=self.loc_y, loc_z=self.loc_z, 
                    loc_z_offset=self.loc_z_offset, rotation=self.rotation, forward_axis=self.forward_axis,
                    frame_start=int(frstart), frame_end=int(frend),
                    root_type='ROOT_MASTER')
                        
        # restore source action
        assign_armature_action(source_rig, bpy.data.actions.get(source_rig_original_action_name), _slot_idx=source_rig_original_slot)
        
        
    # is it already bound?
    is_already_bound = False
    if len(target_rig.keys()):
        if "arp_retarget_bound" in target_rig.keys():
            if target_rig["arp_retarget_bound"] == True:
                is_already_bound = True
    
    if is_already_bound:
        if (self.bind_only and self.unbind) or (self.bind_only == False):
            print("  Unbinding...")
            
            if len(target_rig.keys()):
                if "arp_retarget_ik_chains" in target_rig.keys():
                    ik_chains = target_rig["arp_retarget_ik_chains"]
                    found_ik_dict = True

            
            # Delete remap constraints
            for pose_bone in context.active_object.pose.bones:
                for cns in pose_bone.constraints:
                    if 'REMAP' in cns.name:                    
                        pose_bone.constraints.remove(cns)                        
            
            
            try:# it has been already bound
                bpy.ops.pose.select_all(action='DESELECT')
            except:
                pass

            print("  Deleting bones...")
            # Delete helper bones
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            set_active_object(scn.source_rig)
            
            bpy.ops.object.mode_set(mode='EDIT')
            
            removed_bones = []        
            for ebone in source_rig.data.edit_bones:
                del_ebone = 'arp_remap_temp_bone' in ebone.keys()
                if del_ebone:
                    removed_bones.append(ebone.name)
                    delete_edit_bone(ebone)
                    
                     
            print("  Delete helper bones keyframes...")
            action_name = source_rig.animation_data.action.name
            slot_i = 0
            if bpy.app.version >= (4,4,0):
                slot_i = get_action_slot_idx(source_rig.animation_data.action, source_rig.animation_data.action_slot)
            
            fcurves = get_action_fcurves(bpy.data.actions[action_name], slot_idx=slot_i, as_list=True)
            print("  action name:", action_name)
            for fc in fcurves:
                dp = fc.data_path
                if not dp.startswith("pose.bones"):
                    continue
                bone_name = dp.split('"')[1] 
                
                if bone_name in removed_bones:
                    delete_fcurve(bpy.data.actions[action_name], fc)
                    
            bpy.ops.object.mode_set(mode='POSE')
            bpy.ops.object.mode_set(mode='OBJECT')

            # Clean IK poles keyframes when chains are straight    
            if self.bind_only == False:
                if self.clean_ik_pole:
                    print("  Clean IK pole keyframes...")
                 
                    angle_tolerance = self.clean_ik_pole_angle

                    for keyframe in fcurves[0].keyframe_points:
                        cframe = keyframe.co[0]
                        if int(cframe) < self.frame_start or int(cframe) > self.frame_end:
                            continue
                        #check angle at each frames
                        #scn.frame_current = keyframe.co[0]
                        scn.frame_set(int(cframe))

                        for key, value in ik_chains.items():
                            bone1 = get_object(scn.source_rig).pose.bones[value[0]]
                            bone2 = get_object(scn.source_rig).pose.bones[value[1]]
                            chain_angle = bone1.y_axis.angle(bone2.y_axis)

                            if math.degrees(chain_angle) < angle_tolerance:
                                #remove keyframe, just interpolate
                                pole_bone = get_object(scn.target_rig).pose.bones[value[2]]
                                pole_bone.keyframe_delete(data_path="location")
                                    
                

            # restore source rig pos
            try:# for now does not work with "decoupled" retargetting
                get_object(scn.source_rig).location = source_armature_init_pos
            except: pass

            #update hack
            bpy.ops.object.mode_set(mode='OBJECT')
            scn.frame_set(scn.frame_current)

            # restore initial armature visibility
            get_object(scn.target_rig).hide_viewport = armature_hidden

            # delete proxy local copy if any            
            armature_local = get_object(scn.target_rig + "_local")
            if armature_local:
                bpy.data.objects.remove(armature_local, do_unlink=True)

            # save the binding state in a prop
            target_rig["arp_retarget_bound"] = False
            

    else:
        if self.unbind:            
            self.report({'INFO'}, "Already unbound")

    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    
    # hacky fix for proxy update issue
    if target_rig.animation_data:
        act = target_rig.animation_data.action
        target_rig.animation_data.action = None
        assign_armature_action(target_rig, act)
    
    if bpy.app.version >= (4,0,0):
        remap_collec = get_armature_collections(source_rig).get('remap01')
        if remap_collec:
            remap_collec.is_visible = False
    else:
        source_rig.data.layers[24] = False

    print("Retargetting done.\n")
    scn.frame_set(current_frame)

    
def get_target_bone_name(src_name):
    scn = bpy.context.scene
    for item in scn.bones_map_v2:
        if item.source_bone == src_name:         
            return item.name
    return None
            

def update_set_as_root(self, context):
    scene = context.scene
    if scene.arp_remap_allow_root_update:
        # set all other 'set_as_root' property False (only one possible)
        for i in range(0, len(scene.bones_map_v2)):
            item = scene.bones_map_v2[i]
            if item.set_as_root and i != scene.bones_map_index:
                item.set_as_root = False
            
            if i == scene.bones_map_index:
                item.ik = False
                item.location = False


class SourceNodes(PropertyGroup):
    source_name: StringProperty(default='')
                
                
class BoneRemapSettings(PropertyGroup):# obsolete, keep it for backward-compatibility
    # implicit "name" property = target bone    
    source_bone : EnumProperty(items=bonesmap_source_items, name = "Source  List", description="Source Bone Name")
    x_inv : BoolProperty(name = "X Axis Inverted", default = True, description = 'Inverse the X axis')
    y_inv : BoolProperty(name = "Y Axis Inverted", default = False, description = 'Inverse the Y axis')
    z_inv : BoolProperty(name = "Z Axis Inverted", default = False, description = 'Inverse the Z axis')
    id : IntProperty()
    set_as_root : BoolProperty(name = "Set As Root", default = False, description = 'Set this bone as the root (hips) of the armature ', update=update_set_as_root)    
    offset_rot_x : FloatProperty(name = "Offset X Rotation", default = 0.0, description = 'Offset X rotation value')
    offset_rot_y : FloatProperty(name = "Offset Y Rotation", default = 0.0, description = 'Offset Y rotation value')
    offset_rot_z : FloatProperty(name = "Offset Z Rotation", default = 0.0, description = 'Offset Z rotation value')

    ik : BoolProperty(name="IK", default=False, description="Use IK remapping, similar to world space location (useful for accurate feet tracking)")
    ik_pole : StringProperty(default="", description="IK pole bone (optional)")
    ik_world: BoolProperty(name='IK', default=False, description='Use world IK coordinates instead of relative, works better if the character is spinning')
    #ik_auto_pole : BoolProperty(name="Auto Pole (Target)", default=False, description="The pole bone will inherit the target bone transforms, instead of trying to match the IK chain orientation.\nUseful to avoid IK flips")
    #ik_auto_pole_chain : BoolProperty(name="Auto Pole (Chain)", default=False, description="The pole bone will inherit the IK bones chain transforms, instead of trying to match the IK chain orientation.\nUseful to avoid IK flips")
    ik_auto_pole: EnumProperty(items=(
        ('ABSOLUTE', 'Absolute', 'Evaluate the real IK pole position based on the chain true pole vector\nMay cause IK flip when the IK chain is straight'), 
        ('RELATIVE_TARGET', 'Relative: Target', 'Evaluate the IK pole position as a child of the target bone'),
        ('RELATIVE_CHAIN', 'Relative: Chain', 'Evaluate the IK pole position as a child of the IK bones chain')),
        description='How the IK pole position should be evaluated')
    ik_create_constraints: BoolProperty(name="Add IK Const.", default=False, description="Automatically creates IK constraints if the bone has none")
    ik_1: StringProperty(default='')
    ik_2: StringProperty(default='')
    location: BoolProperty(name="Location", description="Use location remapping, relative to the parent bone (local)", default=False)
    IK_axis_correc: bpy.props.EnumProperty(items=(('X', 'X', 'X'),
                                        ('Y', 'Y', 'Y'),
                                        ('Z', 'Z', 'Z'),
                                        ('-X', '-X', '-X'),
                                        ('-Y', '-Y', '-Y'),
                                        ('-Z', '-Z', '-Z')), default='Y', description='Axis used to correct the IK bones straight alignment if necessary', name='IK_axis_correc')
    
    rot_add: FloatVectorProperty(default=(0.0, 0.0, 0.0), subtype='TRANSLATION', size=3)
    loc_add: FloatVectorProperty(default=(0.0, 0.0, 0.0), subtype='TRANSLATION', size=3)
    loc_mult: FloatProperty(default=1.0)
    
    rot_add_bind: FloatVectorProperty(default=(0.0, 0.0, 0.0), subtype='TRANSLATION', size=3)
    loc_add_bind: FloatVectorProperty(default=(0.0, 0.0, 0.0), subtype='TRANSLATION', size=3)
    

class BoneRemapSettingsv2(PropertyGroup):
    # implicit "name" property = target bone
    source_bone : StringProperty(default='', description="Source Bone Name")
    id : IntProperty()
    set_as_root : BoolProperty(name = "Set As Root", default = False, description = 'Set this bone as the root (hips) of the armature ', update=update_set_as_root)
    ik : BoolProperty(name="IK", default=False, description="Use IK remapping, similar to world space location (useful for accurate feet tracking)")
    ik_pole : StringProperty(default="", description="IK pole bone (optional)")
    ik_world: BoolProperty(name='IK', default=False, description='Use world IK coordinates instead of relative, works better if the character is spinning')   
    ik_auto_pole: EnumProperty(items=(
        ('ABSOLUTE', 'Absolute', 'Evaluate the real IK pole position based on the chain true pole vector\nMay cause IK flip when the IK chain is straight'), 
        ('RELATIVE_TARGET', 'Relative: Target', 'Evaluate the IK pole position as a child of the target bone'),
        ('RELATIVE_CHAIN', 'Relative: Chain', 'Evaluate the IK pole position as a child of the IK bones chain')),
        description='How the IK pole position should be evaluated')
    ik_create_constraints: BoolProperty(name="Add IK Const.", default=False, description="Automatically creates IK constraints if the bone has none")
    ik_1: StringProperty(default='')
    ik_2: StringProperty(default='')
    location: BoolProperty(name="Location", description="Use location remapping, relative to the parent bone (local)", default=False)
    IK_axis_correc: bpy.props.EnumProperty(items=(('X', 'X', 'X'),
                                        ('Y', 'Y', 'Y'),
                                        ('Z', 'Z', 'Z'),
                                        ('-X', '-X', '-X'),
                                        ('-Y', '-Y', '-Y'),
                                        ('-Z', '-Z', '-Z')), default='Y', description='Axis used to correct the IK bones straight alignment if necessary', name='IK_axis_correc')
    
    rot_add: FloatVectorProperty(default=(0.0, 0.0, 0.0), subtype='TRANSLATION', size=3)
    loc_add: FloatVectorProperty(default=(0.0, 0.0, 0.0), subtype='TRANSLATION', size=3)
    loc_mult: FloatProperty(default=1.0)    
    rot_add_bind: FloatVectorProperty(default=(0.0, 0.0, 0.0), subtype='TRANSLATION', size=3)
    loc_add_bind: FloatVectorProperty(default=(0.0, 0.0, 0.0), subtype='TRANSLATION', size=3)
    
    
def _export_config(filepath):
    scn = bpy.context.scene
   
    # add extension
    if not filepath.endswith(".bmap"):
        filepath += ".bmap"
    
    file = open(filepath, 'w', encoding='utf8', newline='\n')

    for item in scn.bones_map_v2:
        # pack new props in the first line. Not ideal but best to ensure compatibility with older files. To improve later!
        first_line = ''
        props_list = [item.name, str(item.location), str(item.ik_auto_pole), vec_to_string(item.rot_add), 
                        vec_to_string(item.loc_add), str(item.loc_mult), str(item.ik_create_constraints), str(item.ik_world), str(item.IK_axis_correc)]
        for prop in props_list:
            first_line += prop + '%'        
        file.write(first_line+"\n")
        file.write(item.source_bone+"\n")
        file.write(str(item.set_as_root)+"\n")
        file.write(str(item.ik)+"\n")
        file.write(item.ik_pole+"\n")

    # close file
    file.close()

    
def _import_config(self):
    context = bpy.context
    scn = context.scene
    bones_not_found = []
    
    target_arm = get_object(scn.target_rig)
    source_arm = get_object(scn.source_rig)
    
    # no armatures set, return
    if target_arm == None or source_arm == None:
        return
        
    filepath = self.filepath
    file = None
    try:
        file = open(filepath, 'r') if sys.version_info >= (3, 11) else open(filepath, 'rU')
    except:
        self.report({"ERROR"}, "Filepath is invalid: "+ filepath)
        return
        
    file_lines = file.readlines()
    total_lines = len(file_lines)
    props_count = 5
    bone_counts = total_lines / props_count

    # clear the bone collection
    if self.clear_current:
        if len(scn.bones_map_v2):
            i = len(scn.bones_map_v2)
            while i >= 0:
                scn.bones_map_v2.remove(i)
                i -= 1

    # import items    
    error_load = False

    # is there a prefix?
    prefix = ''
    prefix = scn.remap_source_nodes[0].source_name.split(":")[0]
    #prefix = scn.source_nodes_name_string.split("+")[0].split(":")[0]
    if prefix != "":
        print("Found prefix:", prefix)
  
    preset_data = {}
    
    line = 0
    
    # read settings
    for i in range(0, int(bone_counts)):
        first_line = str(file_lines[line]).rstrip()# target bone name
        first_line_list = first_line.split('%')
        target_bone_name = ""
        
        # read props
        item_location = 'False'# set with default values
        item_ik_auto_pole = 'ABSOLUTE'
        item_rot_add = Vector((0.0, 0.0, 0.0))
        item_loc_add = Vector((0.0, 0.0, 0.0))
        item_loc_mult = 1.0
        item_add_ik_cns = 'False'
        item_ik_world = 'False'
        item_ik_axis_correc = 'Y'
       
        if len(first_line_list) == 1:
            target_bone_name = first_line
        else:# new format, multiple properties in the first line
            target_bone_name = first_line_list[0]
            if len(first_line_list) >= 2:
                item_location = first_line_list[1]
            if len(first_line_list) >= 3:
                item_ik_auto_pole = first_line_list[2]
            if len(first_line_list) >= 4:
                item_rot_add = first_line_list[3].split(',')
                item_rot_add = str_list_to_fl_list(item_rot_add)
            if len(first_line_list) >= 5:
                item_loc_add = first_line_list[4].split(',')
                item_loc_add = str_list_to_fl_list(item_loc_add)
            if len(first_line_list) >= 6:
                item_loc_mult = first_line_list[5]
            if len(first_line_list) >= 7:
                item_add_ik_cns = first_line_list[6]
            if len(first_line_list) >= 8:
                if first_line_list[7] != '':
                    item_ik_world = first_line_list[7]
            if len(first_line_list) >= 9:
                if first_line_list[8] != '':
                    item_ik_axis_correc = first_line_list[8]      
            
        item_target_bone = 'None'
        if target_arm.data.bones.get(target_bone_name):
            item_target_bone = target_bone_name

        found_name = False
        
        preset_source_bone_name = str(file_lines[line+1]).rstrip()# preset source bone name
        preset_set_as_root = str(file_lines[line+2]).rstrip()
        preset_ik = str(file_lines[line+3]).rstrip()
        preset_ik_pole = str(file_lines[line+4]).rstrip()
     
        item_source_bone = ''
        item_set_as_root = string_to_bool(preset_set_as_root)
        item_ik = preset_ik
        item_ik_pole = preset_ik_pole

        # read source-target bones
        #for src_name in scn.source_nodes_name_string.split("+"):
        for n in scn.remap_source_nodes:
            src_name = n.source_name
            if scn.search_and_replace:
                replaced_line = preset_source_bone_name.replace(scn.name_search, scn.name_replace)
                if src_name == replaced_line:
                    item_source_bone = replaced_line
                    found_name = True
            else:
                if src_name == preset_source_bone_name:               
                    item_source_bone = preset_source_bone_name
                    found_name = True
                            
                else:
                    # the preset doesn't match
                    # try to add the prefix (format 'prefix:boenname') and see if there's a match
                    base_preset_src_name = preset_source_bone_name
                    split_preset_src_name = preset_source_bone_name.split(':')                
                    if len(split_preset_src_name) > 1:
                        base_preset_src_name = split_preset_src_name[1]
                        
                    prefix_add_name = prefix + ":" + base_preset_src_name
                    
                    if src_name == prefix_add_name:                        
                        item_source_bone = prefix_add_name
                        found_name = True                 

        if not found_name:
            bones_not_found.append(preset_source_bone_name)
            error_load = True

        line += props_count

        if item_source_bone != '':
            preset_data[item_source_bone] = [item_target_bone, item_set_as_root, item_ik, item_ik_pole, item_location, item_ik_auto_pole, item_rot_add, item_loc_add, item_loc_mult, item_add_ik_cns, item_ik_world, item_ik_axis_correc]

    # close file
    file.close()

    scn.arp_remap_allow_root_update = False# disable it before assigning the set root value, otherwise it's interfering
    
    # set props
    for key, value in sorted(preset_data.items()):
        item = None
        
        # if "clear list" is disabled, look for existing item
        for b_item in scn.bones_map_v2:
            if b_item.source_bone == key:
                item = b_item                
                continue
                
        if item == None:
            item = scn.bones_map_v2.add()
            item.source_bone = key
            
        item.name = value[0]        
        item.set_as_root = value[1]
        item.ik = string_to_bool(value[2])
        item.ik_pole = value[3]
        item.location = string_to_bool(value[4])
        
        if string_to_bool(value[5]) != None:# retro-compatibility, ik_auto_pole is now an Enum no more Boolean
            item.ik_auto_pole = 'ABSOLUTE' if string_to_bool(value[5]) == False else 'RELATIVE_TARGET'
        else:
            item.ik_auto_pole = value[5]        
        item.rot_add = value[6]
        item.loc_add = value[7]
        item.loc_mult = float(value[8])
        item.ik_create_constraints = string_to_bool(value[9])
        item.ik_world = string_to_bool(value[10])
        item.IK_axis_correc = value[11]
        
    scn.arp_remap_allow_root_update = True
    
    if scn.bones_map_index > len(scn.bones_map_v2)-1:
        scn.bones_map_index = len(scn.bones_map_v2)-1
    
    if len(bones_not_found) > 0:
        self.report({'ERROR'}, "Imported, but some preset bones do not exist in the armature:")
        for i in bones_not_found:
            self.report({'ERROR'}, i)            
    
    # end import_config()
          
          
def set_global_scale(context):
    scn = context.scene
    source_rig = get_object(scn.source_rig)
    target_rig = get_object(scn.target_rig)
    try:
        scn.global_scale = source_rig.scale[0] / target_rig.scale[0]
    except:
        pass


def update_source_rig(self, context):   
    scn = context.scene
    # set source action
    if scn.source_rig != '':
        src_rig = get_object(scn.source_rig)
        save_source_action(src_rig)      
    
        # set global scale
        if scn.target_rig != '':
            set_global_scale(context)


def update_target_rig(self,context):
    scn = context.scene    
    # set global scale
    if scn.source_rig != "" and scn.target_rig != "":
        set_global_scale(context)

        
def entries_are_set():
    scn = bpy.context.scene
    return scn.source_action != '' and scn.source_rig != '' and scn.target_rig != ''

    
def find_linked_armature(action):
    # find armature linked to this action
    for _o in bpy.data.objects:
        if _o.type != 'ARMATURE': continue        
        if _o.animation_data == None: continue
        if _o.animation_data.action == None: continue
        
        if _o.animation_data.action == action:
            return _o
            
    return None

            
def convert_in_place(enable_in_place, act_name='', act_slot=0, armature=None):
    scn = bpy.context.scene    
    act = bpy.data.actions.get(act_name)    

    if act:
        if enable_in_place:
            # make sure to keep the base action in file even if not used
            act.use_fake_user = True

            # remove current if any
            act_in_place = bpy.data.actions.get(act_name+'_IN_PLACE')
            if act_in_place:
                bpy.data.actions.remove(act_in_place)
            
            # create new
            act_in_place = act.copy()
            act_in_place.name = act.name+'_IN_PLACE'
            
            # make sure to keep the base action in file even if not used
            act_in_place.use_fake_user = True
            
            if armature:
                assign_armature_action(armature, act_in_place, _slot_idx=act_slot)
            
            # set location fcurves
            start, end = act_in_place.frame_range[0], act_in_place.frame_range[1]
            
            for fc in get_action_fcurves(act_in_place, slot_idx=act_slot, as_list=True):
                if not 'location' in fc.data_path or not 'pose.bones' in fc.data_path:
                    continue
                first_keyf = fc.keyframe_points[0]
                start_value = first_keyf.co[1]
                last_keyf = fc.keyframe_points[len(fc.keyframe_points)-1]
                end_value = last_keyf.co[1]
                delta = end_value-start_value
                for idx in range(0, len(fc.keyframe_points)):
                    keyf = fc.keyframe_points[idx]
                    keyf_tot = len(fc.keyframe_points)-1
                    if keyf_tot > 0:
                        fac = delta/keyf_tot
                        fac = fac * idx
                        keyf.co[1] -= fac
                        
            return act_in_place
            

        else:# switch from 'in place' to base            
            if '_IN_PLACE' in act.name:
                act_base_name = act.name.replace('_IN_PLACE', '')
                
                #   remove in place action
                bpy.data.actions.remove(act)     
                
                # assign base action to armature
                act_base = bpy.data.actions.get(act_base_name)
                if act_base and armature:
                    assign_armature_action(armature, act_base, _slot_idx=act_slot)
            
                return act_base


def update_in_place(self, context):
    scn = context.scene
    rig_name = scn.source_rig
    src_rig = get_object(rig_name)
    
    # update source action in case it has been renamed
    save_source_action(src_rig)
    
    # get source action
    act_name, act_slot = get_source_action_name(get_slot=True)    
        
    act_list = {act_name: src_rig}# action: linked armature
    
    if scn.batch_retarget:
    
        act_list = {}
        
        for act in bpy.data.actions:
            # filter only containing
            if scn.arp_remap_only_containing != '':# filter only containing
                if not scn.arp_remap_only_containing in act.name: continue
                
            # if selected
            if 'arp_remap' in act.keys() and act['arp_remap'] == True:
                if scn.arp_retarget_in_place and not '_IN_PLACE' in act.name:
                    act_list[act.name] = find_linked_armature(act)
                if not scn.arp_retarget_in_place and '_IN_PLACE' in act.name:
                    act_list[act.name] = find_linked_armature(act)
        
    # convert in place
    for act_name in act_list:
        linked_armature = act_list[act_name]
        
        convert_in_place(scn.arp_retarget_in_place, act_name=act_name, act_slot=act_slot, armature=linked_armature)
    
    # update source rig
    update_source_rig(self, context)

    
###########  UI PANEL  ###################
def get_custom_icon(name):
    # a user reported an error when loading custom icons on Mac, if multiple Blender versions are installed
    # due to a disk read permission issue
    # then return a null id -1 if custom_icons is None
    return custom_icons[name].icon_id if custom_icons else -1


class ARP_PT_auto_rig_remap_panel(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ARP"
    bl_label = "Auto-Rig Pro: Remap"
    bl_idname = "ARP_PT_auto_rig_remap"
    bl_options = {'DEFAULT_CLOSED'}


    def draw(self, context):
        layout = self.layout
        object = context.object
        scn = context.scene
        source_rig = get_object(scn.source_rig)
        target_rig = get_object(scn.target_rig)
        redefine_preserve = False
        global custom_icons
        
        if get_object('arp_markers'):# dirty debug, displaying custom icons greyed out are messing with smart markers
            return
        
        redef_state = 0
        if source_rig:
            if 'remap_redefine_rest_pose' in source_rig.keys():
                redef_state = 1   
            if 'remap_redefine_preserve' in source_rig.keys():
                redefine_preserve = source_rig['remap_redefine_preserve']
        
        if redef_state == 0:# when redefine rest pose, do not show main UI
        
            # Update needed!
            if 'bones_map' in scn.keys():
                first_item = scn.bones_map[1]
                if first_item.get('x_inv') == None or first_item.get('x_inv') == False:# was an unused prop, always set to False
                    layout.label(text='Old remap settings found.')
                    layout.label(text='Please Update below:')
                    layout.operator('arp.remap_update', text='Update')
                    return
                    
        
            # help button
            if get_prefs().beginner_mode:
                row = layout.column().row(align=True).split(factor=0.9)        
                row.label(text='')
                but = row.operator('arp.open_link_internet', text='', icon_value=get_custom_icon('question'))
                but.link_string = ard.doc_url+'remap_doc.html'
        
            # Inputs
            row = layout.row()
            row.prop(scn, 'arp_inputs_expand_ui', icon='TRIA_DOWN' if scn.arp_inputs_expand_ui else 'TRIA_RIGHT', icon_only=True, emboss=False)
            row.label(text='Inputs:')
            if scn.arp_inputs_expand_ui:
                layout.label(text='Source Armature:')
                row = layout.row(align=True)
                row.prop_search(scn, 'source_rig', bpy.data, 'objects', text='')
                row.operator('arp.pick_object', text='', icon='EYEDROPPER').action = 'pick_source'
                
                if scn.source_rig != '' and scn.source_action == '':# missing source animation, display error message
                    col = layout.column(align=True)
                    col.label(text='Source armature not animated,', icon='ERROR')
                    col.label(text='cannot build bones list.')
                    col.label(text='If animation was added afterwards,')
                    col.label(text='then pick again the source armature to')
                    col.label(text='update.')
                
                layout.prop(scn, 'arp_retarget_in_place', text='In Place')
                layout.operator('arp.batch_retarget', text='Multiple Source Anim...') #icon='SETTINGS') TODO

                layout.label(text='Target Armature:')
                row = layout.row(align=True)
                row.prop_search(scn, 'target_rig', bpy.data, 'objects', text='')
                row.operator('arp.pick_object', text='', icon='EYEDROPPER').action = 'pick_target'
           
                row = layout.row(align=True)
                col = layout.column(align=True)
                col.operator('arp.auto_scale', text='Auto Scale')
                layout.separator()
                
                
            row = layout.row(align=True)
            if entries_are_set():#display only if entries are set
                row.enabled = True
            else:
                row.enabled = False

            col = layout.column(align=True)
            col.operator('arp.build_bones_list', text='Build Bones List')

            row = col.row(align=True)
            row.operator('arp.retarget', text='Re-Target', icon_value=get_custom_icon('arrow_right'))
            row.prop(scn, 'arp_retarget_decoupled_expand_ui', icon_only=True, icon='SETTINGS')
            if scn.arp_retarget_decoupled_expand_ui:
                p = col.operator('arp.retarget_bind_only', text='Bind Only')
                p.unbind = False
                p = col.operator('arp.retarget_bind_only', text='Unbind Only')
                p.unbind = True
                col.prop(scn, 'arp_show_freeze_warn', text='Show Freeze Warnings')

            if entries_are_set() and target_rig != None:#only if entries are set
                target_armature = target_rig.data.name
                row = layout.row(align=True)
                split = row.split(factor=0.5)
                split.label(text='Source Bones:')
                split.label(text='Target Bones:')
                row = layout.row(align=True)
                row.template_list('ARP_UL_items', '', scn, 'bones_map_v2', scn, 'bones_map_index', rows=2)
                
                col = row.column(align=True)             
                col.operator(ARP_OT_mirror_bones_list.bl_idname, text='', icon_value=get_custom_icon('mirror'))

                layout.operator('arp.retarget_synchro_select', text='', icon='FILE_REFRESH')

                # Display bone item properties
                if len(scn.bones_map_v2) > 0:
                    # make a box UI
                    box = layout.box()
                    row = box.row(align=True)

                    #row.prop(scn.bones_map[scn.bones_map_index], 'source_bone', text='')
                    row.label(text=scn.bones_map_v2[scn.bones_map_index].source_bone+':' )
                    row.prop_search(scn.bones_map_v2[scn.bones_map_index], 'name', bpy.data.armatures[target_armature], 'bones', text='')
                    row.operator('arp.pick_object', text='', icon='EYEDROPPER').action = 'pick_bone'

                    row = box.row(align=True)
                    row.prop(scn.bones_map_v2[scn.bones_map_index], 'set_as_root', text='Set as Root')                   
                    
                    row = row.row()
                    row.enabled = not scn.bones_map_v2[scn.bones_map_index].ik and not scn.bones_map_v2[scn.bones_map_index].set_as_root
                    row.prop(scn.bones_map_v2[scn.bones_map_index], 'location', text='Location (Local)')                    
                    
                    row=box.row(align=True)
                    split = row.split(factor=0.2)

                    if scn.bones_map_v2[scn.bones_map_index].set_as_root:
                        split.enabled = False                
                    else:
                        split.enabled = True

                    split.prop(scn.bones_map_v2[scn.bones_map_index],'ik', text='IK')
                    if scn.bones_map_v2[scn.bones_map_index].ik:
                        split2 = split.split(factor=0.9, align=True)
                        if scn.bones_map_v2[scn.bones_map_index].ik:
                            split2.enabled = True
                        else:
                            split2.enabled = False
                        split2.prop_search(scn.bones_map_v2[scn.bones_map_index], 'ik_pole', bpy.data.armatures[target_armature], 'bones', text='Pole')
                        split2.operator('arp.pick_object', text='', icon='EYEDROPPER').action = 'pick_pole'
                        
                        row = box.row(align=False)
                        row.enabled = scn.bones_map_v2[scn.bones_map_index].ik
                        row.prop(scn.bones_map_v2[scn.bones_map_index], 'ik_world', text='IK World Space')
                        
                        row = box.row(align=False)
                        row.enabled = scn.bones_map_v2[scn.bones_map_index].ik
                        row.prop(scn.bones_map_v2[scn.bones_map_index], 'ik_auto_pole', text='')
                        row.prop(scn.bones_map_v2[scn.bones_map_index], 'ik_create_constraints')
                        row = box.row(align=False)
                        row.enabled = scn.bones_map_v2[scn.bones_map_index].ik
                        row.label(text='IK Axis Correc:')
                        row.prop(scn.bones_map_v2[scn.bones_map_index], 'IK_axis_correc', text='')

                    col1 = box.column(align=True)
                    row = col1.row(align=True)
                    
                    is_already_bound = False
                    if len(target_rig.keys()):
                        if 'arp_retarget_bound' in target_rig.keys():
                            if target_rig['arp_retarget_bound']:
                                is_already_bound = True
                                
                    twk_text = 'Interactive Tweaks (Bind Mode)' if is_already_bound else 'Interactive Tweaks'
                    row.prop(scn, 'arp_remap_show_tweaks', icon='HIDE_OFF', text=twk_text)
                    row.operator('arp.retarget_clear_tweaks', text='', icon='PANEL_CLOSE')
                    
                    if scn.arp_remap_show_tweaks:
                        col = box.column(align=True)
                        col.prop(scn, 'additive_rot', text='Additive Rotation')
                        row = col.row(align=True)
                        btn = row.operator('arp.apply_offset', text='+X')
                        btn.value = 'rot_+x'
                        btn = row.operator('arp.apply_offset', text='-X')
                        btn.value = 'rot_-x'
                        btn = row.operator('arp.apply_offset', text='+Y')
                        btn.value = 'rot_+y'
                        btn = row.operator('arp.apply_offset', text='-Y')
                        btn.value = 'rot_-y'
                        btn = row.operator('arp.apply_offset', text='+Z')
                        btn.value = 'rot_+z'
                        btn = row.operator('arp.apply_offset', text='-Z')
                        btn.value = 'rot_-z'

                        col = box.column(align=True)
                        col.prop(scn, 'additive_loc', text='Additive Location')
                        row = col.row(align=True)
                        btn = row.operator('arp.apply_offset', text='+X')
                        btn.value = 'loc_+x'
                        btn = row.operator('arp.apply_offset', text='-X')
                        btn.value = 'loc_-x'
                        btn = row.operator('arp.apply_offset', text='+Y')
                        btn.value = 'loc_+y'
                        btn = row.operator('arp.apply_offset', text='-Y')
                        btn.value = 'loc_-y'
                        btn = row.operator('arp.apply_offset', text='+Z')
                        btn.value = 'loc_+z'
                        btn = row.operator('arp.apply_offset', text='-Z')
                        btn.value = 'loc_-z'
                        
                        if not is_already_bound:
                            col = box.column(align=True)
                            col.prop(scn, 'loc_mult', text='Location Multiplier')
                            row = col.row(align=True)
                            btn = row.operator('arp.apply_offset', text='Set')
                            btn.value = 'loc_mult'

                    row = layout.row()
                    row.prop(scn, 'arp_map_presets_expand_ui',
                    icon='TRIA_DOWN' if scn.arp_map_presets_expand_ui else 'TRIA_RIGHT', icon_only=True, emboss=False)
                    row.label(text='Mapping Presets:')

                    if scn.arp_map_presets_expand_ui:                  
                        row = layout.row(align=True)
                        row.operator('arp.import_config', text='Import')
                        row.menu('ARP_MT_remap_import', text='', icon='DOWNARROW_HLT')
                        row = row.row(align=True)
                        row.operator('arp.export_config', text='Export') 
                        row.menu('ARP_MT_remap_export', text='', icon='DOWNARROW_HLT')                    
                        row = layout.row(align=True)
                        row.prop(scn, 'search_and_replace', text='Replace Namespace:')
                        row = layout.row(align=True)
                        if scn.search_and_replace:
                            row.enabled = True
                        else:
                            row.enabled = False
                        row.prop(scn, 'name_search', text='Search')
                        row.prop(scn, 'name_replace', text='Replace')

            else:
                layout.label(text='Empty bone list')

            layout.separator()
        
        layout.alignment = 'CENTER'
        layout.label(text='Redefine Source Rest Pose:')       

        if redef_state == 0:
            layout.operator('arp.redefine_rest_pose', text='Redefine Rest Pose')
        elif redef_state == 1:
            layout.operator('arp.copy_bone_rest', text='Copy Selected Bones Rotation', icon='COPYDOWN')
            row = layout.row(align=True)
            row.operator('arp.cancel_redefine', text='Cancel')
            if redefine_preserve:
                row.operator('arp.save_pose_rest', text='Apply')
            else:
                row.operator('arp.copy_raw_coordinates', text='Apply')         


###########  REGISTER  ##################

classes = (ARP_OT_mirror_bones_list, ARP_OT_clear_tweaks, ARP_OT_synchro_select, ARP_UL_items, ARP_OT_freeze_armature, ARP_OT_redefine_rest_pose, 
ARP_OT_auto_scale, ARP_OT_apply_offset, ARP_OT_cancel_redefine, ARP_OT_copy_bone_rest, ARP_OT_copy_raw_coordinates, 
ARP_OT_pick_object, ARP_OT_export_config, ARP_OT_import_config, ARP_OT_retarget, ARP_OT_build_bones_list, BoneRemapSettings, 
BoneRemapSettingsv2, SourceNodes, ARP_PT_auto_rig_remap_panel, ARP_OT_bind_only, ARP_MT_remap_import, ARP_MT_remap_export, 
ARP_OT_remap_export_preset, ARP_OT_import_config_preset, ARP_OT_save_pose_rest, ARP_OT_batch_retarget,
ARP_OT_toggle_action_remap, ARP_OT_enable_all_actions, ARP_OT_disable_all_actions, ARP_OT_remap_update, 
ARP_OT_remap_export_act_list, ARP_OT_remap_import_act_list)


def update_arp_tab():
    try:
        bpy.utils.unregister_class(ARP_PT_auto_rig_remap_panel)
    except:
        pass
    ARP_PT_auto_rig_remap_panel.bl_category = get_prefs().arp_tab_name
    bpy.utils.register_class(ARP_PT_auto_rig_remap_panel)
    

def register():
    from bpy.utils import register_class

    for cls in classes:
        try:
            register_class(cls)
        except:
            pass

    update_arp_tab()
    update_remap_presets()
    
    global custom_icons
    custom_icons = auto_rig.custom_icons
    
    bpy.types.Scene.target_rig = StringProperty(name = 'Target Rig', default='', description='Destination armature to re-target the action', update=update_target_rig, options={'HIDDEN'})
    bpy.types.Scene.source_rig = StringProperty(name = 'Source Rig', default='', description='Source rig armature to take action from', update=update_source_rig, options={'HIDDEN'})
    bpy.types.Scene.bones_map = bpy.props.CollectionProperty(type=BoneRemapSettings, options={'HIDDEN'})# old prop, keep it for backward-compatibility
    bpy.types.Scene.bones_map_v2 = bpy.props.CollectionProperty(type=BoneRemapSettingsv2, options={'HIDDEN'})
    bpy.types.Scene.bones_map_index = IntProperty(options={'HIDDEN'})
    bpy.types.Scene.global_scale = FloatProperty(name='Global Scale', default=1.0, description='Global scale offset for the root location', options={'HIDDEN'})
    bpy.types.Scene.source_nodes_name_string = StringProperty(name = 'Source Names String', default='', options={'HIDDEN'})# old prop, keep it for backward-compatibility
    bpy.types.Scene.remap_source_nodes = bpy.props.CollectionProperty(type=SourceNodes, options={'HIDDEN'})
    bpy.types.Scene.source_action = StringProperty(name = 'Source Action', default='', description='Source action data to load data from', options={'HIDDEN'})
    bpy.types.Scene.arp_inherit_rot = BoolProperty(name='ARP Inherit Rotation', default=False, description='Auto-Rig Pro type armature only: if enabled, the bones hierarchy will be modified so that the arms and the head will inherit their parent bones rotation.', options={'HIDDEN'})    
    bpy.types.Scene.additive_rot = FloatProperty(name='Additive Rotation', default=math.radians(10), unit='ROTATION', options={'HIDDEN'})
    bpy.types.Scene.additive_loc = FloatProperty(name='Additive Location', default=1.0, options={'HIDDEN'})
    bpy.types.Scene.loc_mult = FloatProperty(name='Root Scale', default=0.9, options={'HIDDEN'})
    bpy.types.Scene.name_search = StringProperty(name='Name search', default='', options={'HIDDEN'})
    bpy.types.Scene.name_replace = StringProperty(name='Replace', default='', options={'HIDDEN'})
    bpy.types.Scene.search_and_replace = BoolProperty(name='search_and_replace', default=False, options={'HIDDEN'})
    bpy.types.Scene.arp_remap_show_tweaks = BoolProperty(name='Interactive Tweaks', default=False, description='Show the interactive tweaks menu', options={'HIDDEN'})
    bpy.types.Scene.arp_remap_allow_root_update = BoolProperty(name='', default=True, description='Allow update check of the Set as Root prop', options={'HIDDEN'})
    bpy.types.Scene.arp_map_presets_expand_ui = BoolProperty(name='', default=True, description='Expand the mapping presets interface', options={'HIDDEN'})
    bpy.types.Scene.arp_inputs_expand_ui = BoolProperty(name='', default=True, description='Expand the inputs interface', options={'HIDDEN'})
    bpy.types.Scene.arp_retarget_decoupled_expand_ui = BoolProperty(name='', default=False, description='Show advanced features', options={'HIDDEN'})
    bpy.types.Scene.arp_retarget_in_place = BoolProperty(default=False, description='Tries to compensate root motion so that the pelvis stay in place. Only works with cyclic animation (walk, run...)\nA new action is created with an _IN_PLACE suffix', update=update_in_place, options={'HIDDEN'})
    bpy.types.Scene.arp_show_freeze_warn = BoolProperty(default=False, description='Show freeze armature warnings when retargetting, to freeze armature object transforms in case of issues', options={'HIDDEN'})
    bpy.types.Scene.batch_retarget = BoolProperty(default=False, description='Retarget multiple animations.\nIf disabled, only the active one', options={'HIDDEN'})
    bpy.types.Scene.arp_remap_only_containing = StringProperty(default='', description='Filter actions containing the given keywords only')

    
def unregister():

    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)

    del bpy.types.Scene.target_rig
    del bpy.types.Scene.source_rig
    del bpy.types.Scene.bones_map# old prop, keep it for backward-compatibility
    del bpy.types.Scene.bones_map_v2
    del bpy.types.Scene.bones_map_index
    del bpy.types.Scene.global_scale
    del bpy.types.Scene.source_nodes_name_string# old prop, keep it for backward-compatibility
    del bpy.types.Scene.remap_source_nodes
    del bpy.types.Scene.source_action
    del bpy.types.Scene.arp_inherit_rot 
    del bpy.types.Scene.additive_rot
    del bpy.types.Scene.additive_loc
    del bpy.types.Scene.loc_mult
    del bpy.types.Scene.name_search
    del bpy.types.Scene.name_replace
    del bpy.types.Scene.search_and_replace
    del bpy.types.Scene.arp_remap_show_tweaks
    del bpy.types.Scene.arp_remap_allow_root_update
    del bpy.types.Scene.arp_map_presets_expand_ui
    del bpy.types.Scene.arp_inputs_expand_ui
    del bpy.types.Scene.arp_retarget_decoupled_expand_ui
    del bpy.types.Scene.arp_retarget_in_place
    del bpy.types.Scene.arp_show_freeze_warn
    del bpy.types.Scene.batch_retarget
    del bpy.types.Scene.arp_remap_only_containing

