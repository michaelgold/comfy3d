import bpy, bmesh, math, bpy_extras, blf, time, os, json
import platform
from bpy_extras import *
from math import *
import mathutils
from mathutils import *
from mathutils.bvhtree import BVHTree
from . import auto_rig_datas as ard
from . import auto_rig, utils
from .utils import *
from bpy.types import (Operator, Menu)
from bpy.props import IntProperty, FloatProperty, EnumProperty, StringProperty, BoolProperty, FloatVectorProperty, CollectionProperty
from operator import itemgetter
import gpu
from gpu_extras.batch import *
import gpu_extras
from bpy.app.handlers import persistent
import subprocess, threading
import random
from itertools import combinations


#print ("\n Starting Auto-Rig Pro: Smart... \n")

# Global vars
handles=[None]


##########################  CLASSES  ##########################


class ARP_OT_facial_setup(Operator):
    """Setup the facial markers"""

    bl_idname = "id.facial_setup"
    bl_label = "facial_setup"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        if get_object('arp_facial_setup') == None:
            return True
        if is_object_hidden(get_object('arp_facial_setup')):
            return True
        return False

    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False

        try:
            _facial_setup()
            
            update_smart_ears(self, context)
            update_smart_eyebrows(self, context)
            update_smart_eyes(self, context)
            update_smart_nose(self, context)
            update_smart_mouth(self, context)
            update_smart_cheeks(self, context)
            update_smart_chin(self, context)

        finally:
            context.preferences.edit.use_global_undo = use_global_undo
            
        return {'FINISHED'}


class ARP_OT_cancel_facial_setup(Operator):
    """Cancel the facial markers setup"""

    bl_idname = "id.cancel_facial_setup"
    bl_label = "cancel_facial_setup"
    bl_options = {'UNDO'}

    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False

        try:
            _cancel_facial_setup()

        finally:
            context.preferences.edit.use_global_undo = use_global_undo
        return {'FINISHED'}
        
        
class ARP_OT_validate_facial_setup(Operator):
    """Validate the facial markers setup"""

    bl_idname = "id.validate_facial_setup"
    bl_label = "validate_facial_setup"
    bl_options = {'UNDO'}

    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False

        try:
            _validate_facial_setup()

        finally:
            context.preferences.edit.use_global_undo = use_global_undo
        return {'FINISHED'}


class ARP_OT_restore_markers(Operator):
    """Restore the markers position from the previous session"""

    bl_idname = "id.restore_markers"
    bl_label = "restore_markers"
    bl_options = {'UNDO'}


    def execute(self, context):        
        scn = context.scene
        
        # make sure all body markers are saved if facial is saved too (markers are created in chronological order, first body then facial)      
        if scn.arp_smart_type == 'BODY' and len(scn.arp_facial_markers_save):
            saved_markers = [item.name for item in scn.arp_markers_save]            
            
            for mname in ['neck', 'chin', 'shoulder', 'hand', 'root', 'foot']:
                if not mname + '_loc' in saved_markers:
                    print("Missing marker: "+mname.upper())
                    self.report({'ERROR'}, "Cannot restore, the previous session is missing body markers")
                    return {'FINISHED'}   
                    
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False
    
        try:
            _restore_markers()
            update_sym(self,context)

        finally:
            context.preferences.edit.use_global_undo = use_global_undo
        return {'FINISHED'}


class ARP_OT_turn(Operator):
    """Turn the character to face the camera"""

    bl_idname = "id.turn"
    bl_label = "turn"
    bl_options = {'UNDO'}

    action : StringProperty()

    @classmethod
    def poll(cls, context):
        return (context.active_object != None)

    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False

        try:
            _turn(context, self.action)

        finally:
            context.preferences.edit.use_global_undo = use_global_undo
        return {'FINISHED'}


class ARP_OT_get_selected_objects(Operator):
    """Select the character meshes objects then click it to quicky place the reference bones on the character"""

    bl_idname = "id.get_selected_objects"
    bl_label = "Smart"
    bl_options = {'UNDO'}
    
   
    @classmethod
    def poll(cls, context):
        if context.active_object:
            if len(context.selected_objects):
                if context.active_object.type == 'MESH' and is_object_hidden(context.active_object) != True:
                    return True
                
                
    def invoke(self, context, event):
        # dialog box
        wm = context.window_manager
        return wm.invoke_props_dialog(self)
        
        
    def draw(self, context):
        layout = self.layout
        layout.prop(context.scene, "arp_smart_type", expand=True)


    def execute(self, context):
        scn = context.scene
        
        bpy.ops.object.mode_set(mode='OBJECT')

        # check units scale
        unit_system = scn.unit_settings
        message = 'Scene unit scale not set to 1.0! May give inaccurate results'
        if unit_system.system != 'None':
            if round(unit_system.scale_length, 3) != 1.0:
                self.report({"WARNING"},message.upper())

        
        # get only mesh objects
        selected_objs = [i for i in context.selected_objects if i.type == 'MESH']        
      
        # store current visibility states of all objects
        for obj in bpy.data.objects:
            obj['arp_smart_viz_state'] = [obj.hide_get(), obj.hide_viewport]
        
        
        bpy.ops.object.select_all(action='DESELECT')

        
        # duplicate  
        for ob in selected_objs:
            ob['arp_body_mesh'] = 1# add a 'arp_body_mesh' tag to the objects
            obj_dupli = duplicate_object(method='data', obj=ob)
            set_active_object(obj_dupli.name)
                
        # remove shape keys if any
        for obj in bpy.context.selected_objects:
            if obj.data.shape_keys:
                sk = obj.data.shape_keys.key_blocks
                # create new shape from mix
                new_sk = obj.shape_key_add(name='FINALMESH', from_mix=True)
                # delete other shapes
                for kb in sk:
                    if kb.name != 'FINALMESH':
                        obj.shape_key_remove(kb)
                # delete new shape last to preserve the shape
                obj.shape_key_remove(new_sk)
                
        # remove prone-to-error modifiers
        buggy_mods = ['SOLIDIFY']
        for obj in bpy.context.selected_objects:
            if len(obj.modifiers):
                for mod in obj.modifiers:
                    if mod.type in buggy_mods:
                        obj.modifiers.remove(mod)
            
        # freeze and join all
        bpy.ops.object.convert(target='MESH')
        bpy.ops.object.join()
        
        # rename
        context.active_object.name = 'body_temp'
        body_temp = get_object(context.active_object.name)
        
        # set euler rotations
        context.active_object.rotation_mode = 'XYZ'
    
        # remove prop on the copy, must be only the original meshes
        del context.active_object['arp_body_mesh']

        # remove any animation data
        try:
            body_temp.animation_data.action = None
        except:
            pass

        # disable X Mirror
        body_temp.data.use_mirror_x = False
        body_temp.data.use_mirror_topology = False

        # hide visibility
        for obj in bpy.data.objects:
            # is object in view layer context?
            found = False
            
            for i in bpy.context.view_layer.objects:
                if i == obj:
                    found=True
                    break

            if found:
                if not obj.select_get():
                    if is_object_hidden(obj) == False:
                        hide_object_visual(obj)
                        obj['arp_smart_hidden'] = True# tag it

        # hide from selection
        for obj in selected_objs:
            if obj.hide_select == False:
                obj.hide_select = True
                obj['arp_smart_selection_hidden'] = True
       

        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False

        try:            
            _get_selected_objects()
            
        finally:
            context.preferences.edit.use_global_undo = use_global_undo

        return {'FINISHED'}  


def AI_files_fingers_checked():
    if not os.path.exists(os.path.join(get_AI_path(root_dir=True), 'info.dat')):
        return False
        
    for model_name in ['fingers_model.pth', 'fingers4_model.pth']:
        if not os.path.exists(os.path.join(get_AI_path(), model_name)):
            return False
    return True  
    
    
def AI_files_check_version(required_version):
    fp_info = os.path.join(get_AI_path(root_dir=True), 'info.dat')
    if not os.path.exists(fp_info):
        return False
        
    with open(fp_info, "r", encoding="utf-8") as f:
            first_line = f.readline().strip()
            if first_line.startswith("version="):
                current_version = float(first_line.split("=", 1)[1].strip())
                print('current version', current_version, 'required', required_version)
                return current_version >= required_version
    return False


class ARP_OT_go_detect(Operator):
    """Start the automatic detection"""

    bl_idname = 'id.go_detect'
    bl_label = ''
    bl_options = {'UNDO'}

    arm_angle_x : FloatProperty(default=0.0)
    fingers_detection_success_l : BoolProperty(default=True)
    fingers_detection_success_r : BoolProperty(default=True)
    error_during_auto_detect : BoolProperty(default=False)
    rig_added: BoolProperty(default=False)
    overwritten_rig = ''    
    rigs_found_items = []
    error_message = ''

    @classmethod
    def poll(cls, context):
        return (context.active_object != None)
   
    
    def invoke(self, context, event):
        scn = context.scene
        
        if scn.arp_fingers_to_detect < 4 or not scn.arp_smart_depth:# AI only supports 5 or 4 fingers for now, and markers depth is required for the hand tip.
            scn.arp_smart_fingers_engine = 'LEGACY'
        
        # check AI files integrity
        if scn.arp_smart_fingers_engine == 'AI':
            if not AI_files_fingers_checked():
                err_mess = 'Fingers AI files are missing or not up to date\nPlease download the latest version or switch the fingers engine to "Voxel Centroids"'
                self.report({'ERROR'}, err_mess)
                return {'FINISHED'}
                
        def trim_name_id(string):
            trimmed_string = string[3:]
            return trimmed_string

        # -- Initial checks
        #   Make sure all markers are set
        if scn.arp_smart_type == 'BODY':
            for mname in ['chin', 'foot', 'hand', 'neck', 'root', 'shoulder']:
                if get_object(mname + '_loc') == None:
                    self.report({'ERROR'}, "Missing marker: "+mname.upper())
                    return {'FINISHED'}   
            
        arp_facial_setup = get_object('arp_facial_setup')
        
        if scn.arp_smart_type == 'FACIAL':
            if arp_facial_setup == None:
                self.report({'ERROR'}, "Facial not set")
                return {'FINISHED'}        
        
        # Reveal temp mesh object
        b_name = scn.arp_body_name
        temp_body = get_object(b_name)
        set_vis_body_tmp(temp_body, 'SHOW')        
            
        if arp_facial_setup:
            unhide_object(arp_facial_setup)
            
            if scn.arp_smart_eyes:
                # valid eyeball object?
                found_eyes_object = True
            
                # check first eyeball
                eyeball1 = get_object(scn.arp_eyeball_name)
                if eyeball1 == None:
                    found_eyes_object = False
                    trimmed_name = trim_name_id(scn.arp_eyeball_name)
                    obj_trimmed = get_object(trimmed_name)# may be not found because of the 3 spaces for ID state description, try to trim it
                    if obj_trimmed:
                        found_eyes_object = True
                        scn["arp_eyeball_name"] = trimmed_name

                # check second eyeball
                if scn.arp_eyeball_type == "SEPARATE" and found_eyes_object:
                    eyeball2 = get_object(scn.arp_eyeball_name_right)
                    if eyeball2 == None:
                        found_eyes_object = False
                        trimmed_name = trim_name_id(scn.arp_eyeball_name_right)
                        obj_trimmed = get_object(trimmed_name)# may be not found because of the 3 spaces for ID state description, try to trim it
                        if obj_trimmed:
                            found_eyes_object = True
                            scn["arp_eyeball_name_right"] = trimmed_name

                if not found_eyes_object:
                    mess = "Eyeball object(s) undefined or does not exist.\nMake sure the eyeball name is correct"
                    print(mess)
                    set_vis_body_tmp(temp_body, 'HIDE')
                    _facial_setup()
                    self.report({'ERROR'}, mess)
                    return {'FINISHED'}
                
            # make sure all facial objects are accessible
            for prop_name in ["arp_eyeball_name", "arp_eyeball_name_right", "arp_tongue_name", "arp_teeth_name", "arp_teeth_lower_name"]:
                if not prop_name in scn.keys():
                    continue    
                
                obj = get_object(scn[prop_name])
                if obj == None:# not set
                    continue
                    
                # enable collections
                for col in obj.users_collection:
                    col.hide_viewport = False
                    col.hide_select = False
                    # enable layers collections
                    layer_col = search_layer_collection(bpy.context.view_layer.layer_collection, col.name)
                    if layer_col:
                        layer_col.exclude = False
                        layer_col.hide_viewport = False
                    
                # unhide
                unhide_object(obj)
                
            
            # Check if all facial setup verts are on the surface mesh               
            # if facial, disable head weights refine (will be skipped anyway when binding, but for clarity)
            scn.arp_bind_chin = False            
                  
            rig_name = bpy.context.active_object.name
            
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            
            set_active_object(arp_facial_setup.name)

            arp_facial_setup.location[1] = -temp_body.dimensions[1] * 40
            mid_verts = [36, 37, 22, 21, 47, 46]
            
            # make planar
            for vert in arp_facial_setup.data.vertices:
                vert.co[1] = 0.0
                # make sure to center mid vertices
                if scn.arp_smart_sym:
                    if vert.index in mid_verts:
                        vert.co[0] = 0.0

            if len(arp_facial_setup.modifiers):
                arp_facial_setup.modifiers.remove(arp_facial_setup.modifiers[0])

            bpy.context.evaluated_depsgraph_get().update()
            
            sw_result = shrinkwrap(arp_facial_setup, temp_body, Vector((0, 1, 0)))            
            
            if not sw_result:               
                arp_facial_setup.location[1] = 0.0
                
                # make planar
                for vert in arp_facial_setup.data.vertices:
                    vert.co[1] = 0.0
                    
                set_vis_body_tmp(temp_body, 'HIDE')
                set_active_object(arp_facial_setup.name)
                bpy.ops.object.mode_set(mode='EDIT')
                self.report({'ERROR'}, "Some facial markers verts are out of the mesh surface.\nMake sure they are all inside.")
                
                return {'FINISHED'}            
     
            
        else:# if no facial, enable head weights refine for better skinning results later
            scn.arp_bind_chin = True
        
        # overwrite?
        if scn.arp_smart_overwrite:
            #   multiple rigs support      
            self.overwritten_rig = ''
         
            if 'rigs_found' in scn.keys():# must be deleted/added to update
                try:# bug reported, leads to an error in some case. Use Try-Except for now. Todo: investigate why!
                    del bpy.types.Scene.rigs_found
                except:
                    pass
            
            if len(self.rigs_found_items):
                self.rigs_found_items = []
            
            for obj in bpy.data.objects:
                if obj.override_library:
                    continue
                if obj.type == "ARMATURE":     
                    if len(obj.keys()):
                        if 'arp_rig_type' in obj.keys() and len(obj.users_collection):# check it is linked to collections. If not, might be orphan data stored deeply in the file...
                            self.rigs_found_items.append((obj.name, obj.name, obj.name))
                            print("  found existing rig:", obj.name)
            
            bpy.types.Scene.rigs_found = EnumProperty(items=self.rigs_found_items)
            
            rigs_found_items = self.rigs_found_items
            
            if len(rigs_found_items):
                if len(rigs_found_items) > 1:                  
                    # open dialog to choose the armature to overwrite
                    wm = context.window_manager
                    return wm.invoke_props_dialog(self, width=400)
                else:
                    self.overwritten_rig = scn.rigs_found                  
        
        
        # if AI fingers not run yet, run it
        if scn.arp_fingers_enable and scn.arp_smart_type != 'FACIAL':
            if scn.arp_smart_fingers_engine == 'AI' and scn.arp_fingers_to_detect in [4, 5]:# only 4-5 are supported by AI for now
                if get_object('thumb1_loc') == None:
                    print("Fingers AI not yet run, run it...")
                    bpy.ops.arp.guess_fingers()
                    
                    if get_object('thumb1_loc') == None:# detection failed, fallback to no fingers
                        scn.arp_fingers_enable = False
        
        self.execute(context)

        return {'PASS_THROUGH'}
        
    
    def draw(self, context):
        scn = context.scene
        layout = self.layout
        layout.label(text='Multiple rigs found, which one should be overwritten?', icon='INFO')      
        layout.prop(scn, 'rigs_found', text='')          
        

    def execute(self, context):
        scn = context.scene
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False
        
        # set fingers amount to 0 if finger detection is disabled
        if scn.arp_fingers_enable == False:
            scn.arp_fingers_to_detect = 0
        
        # restore to defaults
        self.error_during_auto_detect = False
        self.rig_added = False
        self.fingers_detection_success_l = True
        self.fingers_detection_success_r = True
        

        # Save the collections visibility for backup
        collections_visibility = {}
        for col in bpy.data.collections:
            collections_visibility[col.name] = col.hide_viewport        
        
        # append the armature       
        append_arp = False
        rigs_found_items = self.rigs_found_items
        
        if len(rigs_found_items):
            self.overwritten_rig = scn.rigs_found
        
        if scn.arp_smart_overwrite:
            if self.overwritten_rig == '':# no existing arp armature found
                append_arp = True
        else:
            append_arp = True
        
        if append_arp:
            if scn.arp_smart_type == 'BODY':
                auto_rig._append_arp('human')
                
            elif scn.arp_smart_type == 'FACIAL':             
                scn.arp_fingers_to_detect = 0
                auto_rig._append_arp('free')
                auto_rig._add_limb(self, 'head')

            self.rig_added = True
            self.overwritten_rig = context.active_object.name
        
        # Save and set scene settings
        pivot_type = scn.tool_settings.transform_pivot_point# pivot point
        simplify_value = scn.render.use_simplify# simplify
        scn.render.use_simplify = False
        automerge_value = scn.tool_settings.use_mesh_automerge# auto-merge
        scn.tool_settings.use_mesh_automerge = False
        cursor_current_position = scn.cursor.location.copy()# cursor

        # -- Start detecting!
        # Create a parent for temp objects
        bpy.ops.object.mode_set(mode='OBJECT')
        
        bpy.ops.object.empty_add(type='PLAIN_AXES', radius = 1, location=(0,0,0), rotation=(0, 0, 0))
        bpy.context.active_object.name = "arp_temp_detection"
        
        bpy.ops.object.select_all(action='DESELECT')

        try:
            # clear selection
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')

            rig = get_object(self.overwritten_rig)
            
            # make sure to display the armature collection to operate on it. Only do it for
            # the first collection, since the visibility of one collection is prioritzed among other hidden ones
            rig_parent_collections = get_parent_collections(rig.users_collection[0])
            
            for col in rig_parent_collections:
                col.hide_viewport = False

            # unfreeze character selection
            get_object(scn.arp_body_name).hide_select = False
            rig.hide_select = False
            unhide_object(rig)

            # init error values
            self.fingers_detection_success_l = self.fingers_detection_success_r = True

            # Go         
            _auto_detect(self)

            if not self.error_during_auto_detect:
                rig = get_object(self.overwritten_rig, view_layer_change=True)
                set_active_object(self.overwritten_rig)
               
                # simplify, subsurf is slowing down
                simplify_ss_level = scn.render.simplify_subdivision
                scn.render.simplify_subdivision = 0
                scn.render.use_simplify = True
                
                _match_ref(self)
                
                if scn.arp_smart_type == 'BODY':
                    _set_skeleton(self)
                    
                # tag the armature to evaluate if Match to Rig has been performed when exporting or binding
                # to avoid user errors who forget to Match to Rig
                rig.data['has_match_to_rig'] = False
                
                
                # restore subsurf simplify to user value
                scn.render.simplify_subdivision = simplify_ss_level

            bpy.ops.object.mode_set(mode='OBJECT')

            bpy.ops.id.cancel_and_delete_markers()
            _delete_detected()

            # Display the ref bones layer only
            set_active_object(self.overwritten_rig)

            bpy.ops.object.mode_set(mode='EDIT')

            if scn.arp_smart_sym:
                bpy.context.active_object.data.use_mirror_x = True

            enable_layer_exclusive('Reference')           

            # enable in-front display
            bpy.context.active_object.show_in_front = True

            # display the Rig tab
            scn.arp_active_tab = "CREATE"

            # send an info message if the fingers detection failed
            if not self.fingers_detection_success_l or not self.fingers_detection_success_r:
                str = "Fingers detection failed. Try moving the wrist marker closer to the fingers, change the Voxel Precision or Finger Thickness values."
                self.report({'WARNING'}, str)
                return {'FINISHED'}
        
        finally:
            print("--Execute finally instructions...")

            if self.error_during_auto_detect:
                print("  Error during detection, delete markers...")                                       
                # Delete markers
                try:
                    bpy.ops.id.cancel_and_delete_markers()
                except:
                    pass

                # Restore scene collections
                print("  restore collecs...")                             
                for col_name in collections_visibility:
                    bpy.data.collections.get(col_name).hide_viewport = collections_visibility[col_name]

            # Delete temps objects
            if not scn.arp_debug_mode:
                arp_temp_detect_obj = get_object("arp_temp_detection")
                if arp_temp_detect_obj:
                    delete_children(arp_temp_detect_obj, "OBJECT")

                # Restore and set scene settings
                #   pivot point
                scn.tool_settings.transform_pivot_point = pivot_type
                #   simplify
                scn.render.use_simplify = simplify_value
                #   auto merge
                scn.tool_settings.use_mesh_automerge = automerge_value
                #   restore cursor position
                scn.cursor.location = cursor_current_position   

            # Fame the character decently
            bpy.ops.armature.select_all(action='SELECT')
            #bpy.ops.view3d.view_axis(type='FRONT')
            bpy.ops.view3d.view_selected(use_all_regions=False)
            bpy.ops.armature.select_all(action='DESELECT')
            
            # restore undo
            context.preferences.edit.use_global_undo = use_global_undo
            
            if self.error_during_auto_detect:
                auto_rig.display_popup_message(self.error_message, header='Error', icon_type='ERROR')
        
        print("Error during detection?", self.error_during_auto_detect)
        return {'FINISHED'}



class ARP_OT_guess_markers(Operator):
    """Guess markers with deep learning (symmetrical characters only for now)\nLonger to run the first time"""

    bl_idname = "arp.guess_markers"
    bl_label = "Guess Markers"
    
    symmetry: BoolProperty(default=True)
    
    inf_path = ''
    dicts_front = []
    dicts_side = []
    dicts_top = []
    larger_dim = 0.0
    larger_dimy = 0.0
    larger_dimtop = 0.0
    margin = 1.05
    midx = 0.0
    midy = 0.0
    midz = 0.0
    front_samples_rot = []
    side_samples_offset = []
    top_samples_rot = []
   
    def execute(self, context):
        scn = context.scene
        self.front_samples_rot = []
        self.side_samples_offset = []
        self.top_samples_rot = []
        self.dicts_front = []
        self.dicts_side = []
        self.dicts_top = []
        self.inf_path = get_AI_path()
        
        required_version = 1.20
        is_version_ok = AI_files_check_version(required_version)
        if not is_version_ok:
            err_mess = 'AI files are missing or not up to date\nPlease download the latest version: '+str(required_version)
            self.report({'ERROR'}, err_mess)
            return {'FINISHED'}
        
        # screenshot
        _screenshot_char(self)
        
        #  run processes
        cores_amount = os.cpu_count()
        batches = {}
        batch_idx = 1
        thread_batch_idx = 1
        
        for viewpoint in ['front', 'side', 'top']:    
            bin_path = os.path.join(self.inf_path, 'inference_'+viewpoint+'.exe')
            if platform.system() in ['Darwin', 'Linux']:
                bin_path = bin_path[:-4]#rem '.exe'
            
            thresh = None
            if viewpoint == 'top':
                thresh = '0.5'

            images = ''
            tot_samples = scn.arp_smart_AI_body_samples if viewpoint == 'front' else 1# multi samples with side keypoints does not seem to improve the result unfortunately
            for i in range(1, tot_samples+1):
                images += viewpoint+str(i)+'.jpg,'
                    
            thread = threading.Thread(target=run_process, args=(bin_path, images, thresh, None))
            
            if thread_batch_idx < cores_amount-1:# do not exceed the amount of cores
                if not batch_idx in batches:
                    batches[batch_idx] = []
                threads = batches[batch_idx]
                threads.append(thread)
                batches[batch_idx] = threads
                thread_batch_idx += 1                
            else:# new batch
                batch_idx += 1
                thread_batch_idx = 1
                batches[batch_idx] = [thread]
                thread_batch_idx += 1                
        
        for batch_idx in batches:
            print('Running batch:', batch_idx)
            for thread in batches[batch_idx]:
                thread.start()

            # block until complete
            for thread in batches[batch_idx]:
                thread.join()
     
     
        # build markers
        _fetch_keypoints(self)
        _set_markers_from_keypoints(self)
        _screenshot_cleanup(self)
        
        if self.symmetry:
            scn.arp_smart_sym = True
            scn.arp_smart_depth = True
            
        # enable fingers AI
        scn.arp_smart_fingers_engine = 'AI'

        return {'FINISHED'}
        
        
def get_AI_path(root_dir=False):
    AI_path = get_prefs().ai_presets_path    
    if not (AI_path.endswith("\\") or AI_path.endswith('/')):
        AI_path += '/'
    if root_dir:
        return AI_path
    else:
        return os.path.join(AI_path, "inference")
    
        
        
class ARP_OT_guess_fingers(Operator):
    """Guess fingers with deep learning.\nLonger to run the first time"""

    bl_idname = "arp.guess_fingers"
    bl_label = "Guess Fingers"   
    
    inf_path = ''
    keypoints = {}
    cams_data_l = []
    cams_data_r = []
    cam_ortho = 1.0
    hand_idx = 1
    success = True
    
    def execute(self, context):
        scn = context.scene
        if bpy.data.objects.get('hand_tip_loc') == None:
            self.report({'ERROR'}, 'Hand Tip marker is missing.\nClick "Add Optional Markers" to add it')
            return {'FINISHED'}            
            
        # init
        self.cams_data_l = []
        self.cams_data_r = []
        self.keypoints = {}        
      
        
        #  AI path       
        self.inf_path = get_AI_path()
        
        # check files integrity
        if not AI_files_fingers_checked():
            err_mess = 'Fingers AI files are missing or not up to date\nPlease download the latest version or switch the fingers engine to "Voxel Centroids"'
            self.report({'ERROR'}, err_mess)
            return {'FINISHED'}
        
        sides = ['_l']
        if not scn.arp_smart_sym:
            sides.append('_r')
            
        for side in sides:
            print("Screenshot fingers", side)
            _screenshot_fingers(self, side)
        
        #  run process
        bin_path_fingers = os.path.join(self.inf_path, 'inference_fingers.exe')
        if platform.system() in ['Darwin', 'Linux']:
            bin_path_fingers = bin_path_fingers[:-4]#rem '.exe'
        
        hand_images = ''        
        for side in sides:
            for i in range(1, self.hand_idx+1):
                hand_images += f'hand{i}{side}.jpg,'  
                
        thread = threading.Thread(target=run_process, args=(bin_path_fingers, hand_images, str(scn.arp_smart_AI_thresh), str(scn.arp_fingers_to_detect)))
        thread.start()
        thread.join()
      
        # build markers
        for side in sides:
            _fetch_fingers_keypoints(self, side)
            _set_markers_fingers_from_keypoints(self, side)
        
        _screenshot_cleanup(self)
        
        if self.success == False:# failed
            auto_rig.display_popup_message('AI fingers detection failed, likely caused by entangled fingers (curled, fist)\nTry increasing AI Samples, or decreasing Error Threshold, or use Voxel Centroid', header='Error', icon_type='ERROR')
            set_active_object('root_loc')
            
        return {'FINISHED'}
        
        
class ARP_OT_guess_facial(Operator):
    """Guess facial markers with deep learning.\nStill experimental, works best with standard facial design, may not always output accurate results"""

    bl_idname = "arp.guess_facial"
    bl_label = "Guess Facial"   
    
    inf_path = ''
    keypoints = []
    cams_data = []
    cam_ortho = 1.0
    success = True
    facial_samples_rot = []
    
    def execute(self, context):
        scn = context.scene
        if bpy.data.objects.get('chin_loc') == None:
            self.report({'ERROR'}, 'Chin marker is missing')
            return {'FINISHED'}            
            
        # init
        self.facial_samples_rot = []
        self.cams_data = []
        self.keypoints = []
        self.inf_path = get_AI_path()
        
        required_version = 1.17
        is_version_ok = AI_files_check_version(required_version)
        if not is_version_ok:
            err_mess = 'AI files are missing or not up to date for facial markers\nPlease download the latest version: '+str(required_version)
            self.report({'ERROR'}, err_mess)
            return {'FINISHED'}
            
        if get_object('head_tip_loc') == None:
            self.report({'ERROR'}, 'Add the head tip marker first')
            return {'FINISHED'}
            
        print("Screenshot facial")
        _screenshot_facial(self)
        
        #  run process
        bin_path_facial = os.path.join(self.inf_path, 'inference_facial.exe')
        if platform.system() in ['Darwin', 'Linux']:
            bin_path_facial = bin_path_facial[:-4]#rem '.exe'
        
        facial_images = ''
        for i in range(1, scn.arp_smart_AI_facial_samples+1):
            facial_images += f'facial{i}.jpg,'
                    
        thread = threading.Thread(target=run_process, args=(bin_path_facial, facial_images, '0.3', None))
        thread.start()
        thread.join()
        
        # build markers
        _fetch_facial_keypoints(self)
        _set_markers_facial_from_keypoints(self)
        
        _screenshot_cleanup(self)
        
        if self.success == False:# failed
            auto_rig.display_popup_message('AI facial detection failed. Place markers manually', header='Error', icon_type='ERROR')
            set_active_object('root_loc')
        
        return {'FINISHED'}        
        

class ARP_OT_markers_fx(Operator):
    """Markers FX"""

    bl_idname = 'id.markers_fx'
    bl_label = 'markers_fx'

    active : BoolProperty()
    arp_marker_to_select : StringProperty(default='')
    img_name = 'arp_smart_circle'
    img_over_name = 'arp_smart_circle_over'
    img_blue_name = 'arp_smart_circle_blue'
    img_yellow_name = 'arp_smart_circle_yellow'
    img_red_name = 'arp_smart_circle_red'
    img_orange_name = 'arp_smart_circle_orange'
    img_violet_name = 'arp_smart_circle_violet'
    shader_type = 'UNIFORM_COLOR' if bpy.app.version >= (4,0,0) else '2D_UNIFORM_COLOR'
    shader_img_type = '2D_IMAGE' if bpy.app.version < (3,4,0) else 'IMAGE_COLOR'
    num_segments = 64
    radius = 20
    radius_dot = 2
    radius_outline = 22
    # color
    circle_color = (0.0, 0.9, 0.5, 0.3)
    border_color = (0.5, 0.9, 0.5, 0.6)
    center_color = (1, 1, 1, 1)
    blue_color =   (0.0, 0.7, 1.0, 0.8)
    yellow_color = (1.0, 1.0, 0.0, 0.5)
    orange_color = (1.0, 0.5, 0.0, 0.5)
    red_color =    (1.0, 0.0, 0.0, 0.8)
    violet_color = (0.5, 0.3, 0.5, 0.8)
    
    # icon
    img_circle = None
    img_circle_over = None
    img_circle_blue = None
    img_circle_yellow = None
    img_circle_orange = None
    img_circle_violet = None
    img_circle_red = None
    tex = None    
  
    region = None
    region_3d = None
    mouse_x = None
    mouse_y = None
    hotspot_selectable_marker = None    
    mouse_select = None
    
    
    def draw(self, context):
        if bpy.context.scene.arp_disable_smart_fx:
            return
            
        # update datas   
        arp_markers = get_object('arp_markers')
        
        if arp_markers:            
            self.hotspot_selectable_marker = None
            gpu.state.blend_set('ADDITIVE')
            
            for obj in arp_markers.children:
                object_loc_2d = bpy_extras.view3d_utils.location_3d_to_region_2d(self.region, self.region_3d, obj.matrix_world.translation, default=None)

                # parent-child line connection
                par_joint = None
                par_object_loc_2d = None
                #   body
                if obj.name in ['chin_loc', 'root_loc', 'head_tip_loc'] or obj.name.startswith('shoulder_loc'):
                    par_joint = get_object('neck_loc')              
                elif obj.name.startswith('hand_loc'):
                    if get_object('elbow_loc'):
                        par_joint = get_object(obj.name.replace('hand_loc', 'elbow_loc'))
                    else:
                        par_joint = get_object(obj.name.replace('hand_loc', 'shoulder_loc'))
                elif obj.name.startswith('elbow_loc'):
                    par_joint = get_object(obj.name.replace('elbow_loc', 'shoulder_loc'))
                elif obj.name.startswith("hand_tip_loc"):
                    par_joint = get_object(obj.name.replace('hand_tip_loc', 'hand_loc'))
                elif obj.name.startswith('foot_loc'):
                    if get_object('knee_loc'):
                        par_joint = get_object(obj.name.replace('foot_loc', 'knee_loc'))
                    elif get_object('thigh_loc'):
                        par_joint = get_object(obj.name.replace('foot_loc', 'thigh_loc'))
                    else:
                        par_joint = get_object('root_loc')
                elif obj.name.startswith('knee_loc'):
                    par_joint =get_object(obj.name.replace('knee_loc', 'thigh_loc'))
                elif obj.name.startswith('thigh_loc'):
                    par_joint = get_object('root_loc')
                #   fingers
                for fname in ['thumb', 'index', 'middle', 'ring', 'pinky']:
                    for fi in range(1, 5):
                        if obj.name.startswith(fname+str(fi)):
                            if fi == 1:
                                par_joint = get_object(obj.name.replace(fname+str(fi)+'_loc', 'hand_loc'))
                            else:
                                par_joint = get_object(obj.name.replace(fname+str(fi)+'_loc', fname+str(fi-1)+'_loc'))
                
                    
                if par_joint:
                    par_object_loc_2d = bpy_extras.view3d_utils.location_3d_to_region_2d(self.region, self.region_3d, par_joint.matrix_world.translation, default=None)
                        
                if object_loc_2d == None:
                    continue

                _x = object_loc_2d[0]
                _y = object_loc_2d[1]
                
                shader = None
                batch = None            
                            
                shader = gpu.shader.from_builtin(self.shader_img_type)
                scale = 20
                if 'thumb' in obj.name or 'index' in obj.name or 'middle' in obj.name or 'ring' in obj.name or 'pinky' in obj.name:
                    scale = 10
                batch = batch_for_shader(shader, 'TRI_FAN', 
                    {'pos': (( float(_x-scale), float(_y-scale)), (float( _x+scale), float(_y-scale)), (float(_x+scale), float(_y+scale)), (float(_x-scale), float(_y+scale))),
                    'texCoord': ((0, 0), (1, 0), (1, 1), (0, 1))})
                    
                # line connection
                shader_line = None
                batch_line = None
                if par_object_loc_2d:
                    shader_line = gpu.shader.from_builtin(self.shader_type)
                    batch_line = batch_for_shader(shader_line, 'LINES', {'pos': (par_object_loc_2d, object_loc_2d)})

                line_color = self.border_color
                
                # Highlight the selected marker/mouse over     
                self.tex = gpu.texture.from_image(self.img_circle)
                if 'thumb' in obj.name:
                    self.tex = gpu.texture.from_image(self.img_circle_yellow)
                    line_color = self.yellow_color
                if 'index' in obj.name:
                    self.tex = gpu.texture.from_image(self.img_circle_orange)
                    line_color = self.orange_color
                if 'middle' in obj.name:
                    self.tex = gpu.texture.from_image(self.img_circle_red)
                    line_color = self.red_color
                if  'ring' in obj.name:
                    self.tex = gpu.texture.from_image(self.img_circle_violet)
                    line_color = self.violet_color
                if 'pinky' in obj.name:
                    self.tex = gpu.texture.from_image(self.img_circle_blue)
                    line_color = self.blue_color
                    
                final_color = self.circle_color                

                if self.mouse_x:
                    is_in_hotspot = bool((Vector((_x, _y)) - Vector((self.mouse_x, self.mouse_y))).magnitude < 22)
                    if is_in_hotspot:
                        self.hotspot_selectable_marker = obj.name
                    if bpy.context.active_object == obj or is_in_hotspot:                       
                        self.tex = gpu.texture.from_image(self.img_circle_over)
                        

                # Render               
                shader.bind()                    
                shader.uniform_sampler('image', self.tex) 
                batch.draw(shader)                    
                    
                #   line connection
                if par_object_loc_2d:
                    shader_line.bind()
                    shader_line.uniform_float('color', line_color)
                    batch_line.draw(shader_line)
                    
                    
            facial_mesh = get_object('arp_facial_setup')
            
            if facial_mesh and bpy.context.mode == 'EDIT_MESH' and bpy.context.view_layer.objects.active == facial_mesh:
                _mesh = bmesh.from_edit_mesh(facial_mesh.data)

                for vert in _mesh.verts:
                    bname = get_facial_marker_vert_bone(vert.index)
                    if bname == None:
                        continue
                    if vert.hide:
                        continue
                        
                    vert_loc_2d = bpy_extras.view3d_utils.location_3d_to_region_2d(self.region, self.region_3d, facial_mesh.matrix_world @ vert.co, default=None)
                    _x = vert_loc_2d[0]
                    _y = vert_loc_2d[1]                    
                
                    shader = gpu.shader.from_builtin(self.shader_img_type)
                    scale = 10
                    batch = batch_for_shader(shader, 'TRI_FAN', 
                        {"pos": ( (float(_x-scale), float(_y-scale) ), ( float(_x+scale), float(_y-scale)), ( float(_x+scale), float(_y+scale)), ( float(_x-scale), float(_y+scale))),
                        "texCoord": ((0, 0), (1, 0), (1, 1), (0, 1))})
                        
                    shader.bind()
                    
                    self.tex = gpu.texture.from_image(self.img_circle)
                    
                    if 'eyebrow' in bname:   
                        self.tex = gpu.texture.from_image(self.img_circle_yellow)
                    elif 'eyelid' in bname:
                        self.tex = gpu.texture.from_image(self.img_circle_blue)
                    elif 'lips' in bname:
                        self.tex = gpu.texture.from_image(self.img_circle_red)
                    
                    shader.uniform_sampler("image", self.tex) 
                    batch.draw(shader)
                    
                for edge in _mesh.edges:       
                    v1 = edge.verts[0]
                    v2 = edge.verts[1]
                    if v1.hide or v2.hide:
                        continue
                    
                    vert1_loc_2d = bpy_extras.view3d_utils.location_3d_to_region_2d(self.region, self.region_3d, facial_mesh.matrix_world @ v1.co, default=None)
                    vert2_loc_2d = bpy_extras.view3d_utils.location_3d_to_region_2d(self.region, self.region_3d, facial_mesh.matrix_world @ v2.co, default=None)
                    shader_line = gpu.shader.from_builtin(self.shader_type)
                    batch_line = batch_for_shader(shader_line, 'LINES', {'pos': (vert1_loc_2d, vert2_loc_2d)})
                    shader_line.bind()
                    
                    line_color = self.border_color
                    bname = get_facial_marker_vert_bone(v1.index)
                    if 'eyebrow' in bname:   
                        line_color = self.yellow_color
                    if 'eyelid' in bname:   
                        line_color = self.blue_color
                    if 'lips' in bname:   
                        line_color = self.red_color
                    
                    shader_line.uniform_float("color", line_color)
                    batch_line.draw(shader_line)
                
                del _mesh
                
        
    def modal(self, context, event):    
        if bpy.context.scene.arp_disable_smart_fx:
            return
            
        # enable constant update for mouse-over evaluation function
        if context.area:
            context.area.tag_redraw()

        # clicking in a empty space in 2.8 can deselect everything when using Right Click Select
        # workaround to ensure selection by selecting it again
        #print('arp_marker_to_select', context.scene.arp_marker_to_select)
        if context.scene.arp_marker_to_select != "":
            marker_obj = get_object(context.scene.arp_marker_to_select)
            if marker_obj:
                if marker_obj.select_get() == False:
                    if context.mode == "OBJECT":
                        bpy.ops.object.select_all(action='DESELECT')
                        set_active_object(context.scene.arp_marker_to_select)
                        context.scene.arp_marker_to_select = ""

        # end operator
        if get_object('arp_markers') == None or self.active == False or context.scene.arp_quit:
            if bpy.context.scene.arp_debug_mode:
                print('End Markers FX')
            try:
                bpy.types.SpaceView3D.draw_handler_remove(handles[0], 'WINDOW')
            except:
                if bpy.context.scene.arp_debug_mode:
                    print('Handler already removed')
                pass
                
            # clear image cache
            for img_name in [self.img_name, self.img_over_name, self.img_blue_name, self.img_yellow_name, self.img_red_name]:
                img = bpy.data.images.get(img_name)
                if img:
                    bpy.data.images.remove(img)
                    

            return {'FINISHED'}

        self.mouse_x = event.mouse_region_x
        self.mouse_y = event.mouse_region_y

        if event.type == self.mouse_select and context.mode == "OBJECT":
            if self.hotspot_selectable_marker:
                bpy.ops.object.select_all(action='DESELECT')
                set_active_object(self.hotspot_selectable_marker)
                context.scene.arp_marker_to_select = self.hotspot_selectable_marker

        return {'PASS_THROUGH'}


    def execute(self, context):
        # get markers icons
        if self.img_circle == None:
            img = bpy.data.images.get(self.img_name)
            if img == None:
                dir = os.path.dirname(os.path.abspath(__file__))
                addon_dir = os.path.dirname(dir)
                fp = addon_dir + '/icons/circle.png'
                img = bpy.data.images.load(fp)
                img.name = self.img_name
            self.img_circle = img
            
        if self.img_circle_over == None:
            img = bpy.data.images.get(self.img_over_name)
            if img == None:
                dir = os.path.dirname(os.path.abspath(__file__))
                addon_dir = os.path.dirname(dir)
                fp = addon_dir + '/icons/circle_over.png'
                img = bpy.data.images.load(fp)
                img.name = self.img_over_name
            self.img_circle_over = img
            
        if self.img_circle_blue == None:
            img = bpy.data.images.get(self.img_blue_name)
            if img == None:
                dir = os.path.dirname(os.path.abspath(__file__))
                addon_dir = os.path.dirname(dir)
                fp = addon_dir + '/icons/circle_blue.png'
                img = bpy.data.images.load(fp)
                img.name = self.img_blue_name
            self.img_circle_blue = img
            
        if self.img_circle_yellow == None:
            img = bpy.data.images.get(self.img_yellow_name)
            if img == None:
                dir = os.path.dirname(os.path.abspath(__file__))
                addon_dir = os.path.dirname(dir)
                fp = addon_dir + '/icons/circle_yellow.png'
                img = bpy.data.images.load(fp)
                img.name = self.img_yellow_name
            self.img_circle_yellow = img
            
        if self.img_circle_red == None:
            img = bpy.data.images.get(self.img_red_name)
            if img == None:
                dir = os.path.dirname(os.path.abspath(__file__))
                addon_dir = os.path.dirname(dir)
                fp = addon_dir + '/icons/circle_red.png'
                img = bpy.data.images.load(fp)
                img.name = self.img_red_name
            self.img_circle_red = img
            
        if self.img_circle_orange == None:
            img = bpy.data.images.get(self.img_orange_name)
            if img == None:
                dir = os.path.dirname(os.path.abspath(__file__))
                addon_dir = os.path.dirname(dir)
                fp = addon_dir + '/icons/circle_orange.png'
                img = bpy.data.images.load(fp)
                img.name = self.img_orange_name
            self.img_circle_orange = img
            
        if self.img_circle_violet == None:
            img = bpy.data.images.get(self.img_violet_name)
            if img == None:
                dir = os.path.dirname(os.path.abspath(__file__))
                addon_dir = os.path.dirname(dir)
                fp = addon_dir + '/icons/circle_violet.png'
                img = bpy.data.images.load(fp)
                img.name = self.img_violet_name
            self.img_circle_violet = img
        

        # get mouse select button
        self.mouse_select = 'LEFTMOUSE'

        if get_mouse_select() == 'RIGHT':
            self.mouse_select = 'RIGHTMOUSE'

        args = (self, context)
        #first remove previous session handler if any
        try:
            bpy.types.SpaceView3D.draw_handler_remove(handles[0], 'WINDOW')
        except:
            if bpy.context.scene.arp_debug_mode:
                print('No handlers to remove')
            pass

        if self.active == True:
            if bpy.context.scene.arp_debug_mode:
                print('Start Markers FX')
            
            if bpy.context.scene.arp_disable_smart_fx == False:
                handles[0] = bpy.types.SpaceView3D.draw_handler_add(self.draw_callback_3_args, args, 'WINDOW', 'POST_PIXEL')
                context.window_manager.modal_handler_add(self)

            return {'RUNNING_MODAL'}

        return{'CANCELLED'}
        

    def draw_callback_3_args(self, op, context):
        try:
            self.region = context.region
        except:
            return
        self.region_3d = context.space_data.region_3d
        self.draw(self)


class ARP_OT_add_marker(Operator):
    """Add a marker to help auto-detection"""

    bl_idname = "id.add_marker"
    bl_label = "add_marker"
    bl_options = {'UNDO'}

    body_part : StringProperty(name="Body Part")
    body_width : FloatProperty()
    body_height : FloatProperty()
    mouse_select = None
    mouse_deselect = None
    
    @classmethod
    def poll(cls, context):
        return (context.active_object != None)        

    # First create the markers objects
    def execute(self, context):        
        try:
            # disable markers depth by default, when placing manually the markers
            if self.body_part == 'neck':
                context.scene.arp_smart_depth = False
            
            _add_marker(self.body_part, True)
            context.scene.arp_marker_to_select = self.body_part + "_loc"# ensure to select the new marker

        finally:
            pass
            
        return {'FINISHED'}


    def set_marker_pos(self, context, event):        
        new_marker_obj = get_object(self.body_part+"_loc")
        if new_marker_obj == None:
            return

        _region = bpy.context.region
        _region_3d = bpy.context.space_data.region_3d
        new_marker_obj.location = bpy_extras.view3d_utils.region_2d_to_location_3d(_region, _region_3d, (event.mouse_region_x, event.mouse_region_y), new_marker_obj.location)

        #limits
        mid_markers = ['neck', 'root', 'chin', 'head_tip']
        if context.scene.arp_smart_sym:
            if new_marker_obj.location[0] < 0 or self.body_part in mid_markers:
                new_marker_obj.location[0] = 0
                
        if new_marker_obj.location[0] > self.body_width/2:
            new_marker_obj.location[0] = self.body_width/2

        if context.scene.arp_smart_type == 'BODY':
            if new_marker_obj.location[2] > self.body_height:
                new_marker_obj.location[2] = self.body_height

            if new_marker_obj.location[2] < 0:
                new_marker_obj.location[2] = 0

    # Then keep them movable
    def modal(self, context, event):
        
        if event.type == 'MOUSEMOVE':
            self.set_marker_pos(context, event)            

        elif event.type == self.mouse_select or event.type == self.mouse_deselect:            
            if not context.scene.arp_smart_sym:
                sym_marker = get_object(self.body_part+"_loc"+"_sym")
                if sym_marker:
                    final_mat = sym_marker.matrix_world
                    sym_marker.constraints[0].influence = 0.0

                    sym_marker.matrix_world = final_mat

            set_active_object(self.body_part+"_loc")
            return {'FINISHED'}

        elif event.type in {self.mouse_deselect, 'ESC'}:
            #context.active_object.location.x = self.first_value
            return {'CANCELLED'}

        context.area.tag_redraw()

        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        
        scn = context.scene
        self.execute(context)

        #first time launch
        # get mouse selection from user pref
        self.mouse_deselect = 'RIGHTMOUSE'
        self.mouse_select = 'LEFTMOUSE'
        if get_mouse_select() == 'RIGHT':
            self.mouse_select = 'RIGHTMOUSE'
            self.mouse_deselect = 'LEFTMOUSE'

        if scn.arp_smart_type == 'BODY' and self.body_part == 'neck':
            bpy.ops.id.markers_fx(active=True)
        elif scn.arp_smart_type == 'FACIAL' and self.body_part == 'chin':
            bpy.ops.id.markers_fx(active=True)

        self.body_width = get_object(scn.arp_body_name).dimensions[0]
        self.body_height = get_object(scn.arp_body_name).dimensions[2]

        if context.active_object:
            self.set_marker_pos(context, event)
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}

        else:
            self.report({'WARNING'}, "No active object, could not finish")
            return {'CANCELLED'}


class ARP_MT_optional_markers_menu(Menu):
    bl_label = "Optional Markers"
    
    def draw(self, _context):
        layout = self.layout
        if get_object('hand_tip_loc') == None:
            layout.operator("id.add_marker", text="Hand Tip").body_part = 'hand_tip'
        if get_object('thigh_loc') == None:
            layout.operator("id.add_marker", text="Thigh").body_part = 'thigh'
        if get_object('knee_loc') == None:
            layout.operator("id.add_marker", text="Knee").body_part = 'knee'
        if get_object('elbow_loc') == None:
            layout.operator("id.add_marker", text="Elbow").body_part = 'elbow'
        if get_object('head_tip_loc') == None:
            layout.operator("id.add_marker", text="Head Tip").body_part = 'head_tip'
        
            
class ARP_OT_delete_detected(Operator):
    """Delete the detected markers"""

    bl_idname = "id.delete_detected"
    bl_label = "delete_detected"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.active_object != None)

    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False
        try:
            if get_object("auto_detect_loc") == None:
                self.report({'ERROR'}, "No markers found")
                return{'FINISHED'}

            _delete_detected()

        finally:
            context.preferences.edit.use_global_undo = use_global_undo
        return {'FINISHED'}


class ARP_OT_cancel_and_delete_markers(Operator):
    """Cancel the smart detection and delete the markers"""

    bl_idname = "id.cancel_and_delete_markers"
    bl_label = "cancel_and_delete_markers"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.active_object != None)

    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False
        try:
            scn = context.scene
            
            if get_object("arp_markers") == None:
                self.report({'ERROR'}, "No markers found")
                return{'FINISHED'}

            #save current mode
            current_mode = context.mode
            active_obj = context.active_object

            bpy.ops.object.mode_set(mode='OBJECT')

            # unfreeze character selection and restore visibility
            for obj in bpy.data.objects:
                if len(obj.keys()):
                    if 'arp_smart_selection_hidden' in obj.keys():
                        obj.hide_select = False
                        del obj['arp_smart_selection_hidden']
                        
                    if 'arp_smart_hidden' in obj.keys():
                        unhide_object(obj)
                        del obj['arp_smart_hidden']
                
                # delete the 'arp_body_mesh' tag from objects
                if len(obj.keys()):
                    if 'arp_body_mesh' in obj.keys():
                        del obj['arp_body_mesh']
                        
            # restore initial visibility states of all objects
            for obj in bpy.data.objects:
                if 'arp_smart_viz_state' in obj.keys():
                    try:
                        obj.hide_set(obj['arp_smart_viz_state'][0])
                        obj.hide_viewport = obj['arp_smart_viz_state'][1]
                    except:
                        pass
                    del obj['arp_smart_viz_state']


            if 'rigs_found' in scn.keys():
                try:# debug, rigs_found is corrupted in a rare file case, returns 0
                    if get_object(scn.rigs_found):
                        unhide_object(get_object(scn.rigs_found))
                except:
                    pass  

            _cancel_and_delete_markers()

            # restore current mode
            try:
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


 ##########################  FUNCTIONS  ##########################
def set_vis_body_tmp(temp_body, state):
    if temp_body:
        if state == 'SHOW':
            unhide_object(temp_body)
        elif state == 'HIDE':
            hide_object(temp_body)            
                
                
def get_mouse_select():
    active_kc = bpy.context.preferences.keymap.active_keyconfig
    active_pref = bpy.context.window_manager.keyconfigs[active_kc].preferences
    return getattr(active_pref, 'select_mouse', 'LEFT')


def shrinkwrap(source_obj, target_obj, ray_dir):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    scn = bpy.context.scene
    
    ear_verts = []
    eyebrow_verts = []
    nose_verts = ['nose_01.x', 'nose_03.x']
    cheek_verts = []
    eye_verts = [i for i in ard.facial_markers if i.startswith('eyelid')]
    mouth_verts = [i for i in ard.facial_markers if i.startswith('lips')]
    chin_verts = [i for i in ard.facial_markers if i.startswith('chin')]
    
    for s in ['.l', '.r']:
        ear_verts.append(ard.facial_markers['ear_01'+s])
        ear_verts.append(ard.facial_markers['ear_02'+s])
        eyebrow_verts.append(ard.facial_markers['eyebrow_01_end'+s])
        eyebrow_verts.append(ard.facial_markers['eyebrow_01'+s])
        eyebrow_verts.append(ard.facial_markers['eyebrow_02'+s])
        eyebrow_verts.append(ard.facial_markers['eyebrow_03'+s])
        cheek_verts.append(ard.facial_markers['cheek_smile'+s])
        cheek_verts.append(ard.facial_markers['cheek_inflate'+s])
    
    for vert in source_obj.data.vertices:
        if scn.arp_smart_ears == False:
            if vert.index in ear_verts:
                continue
        
        if scn.arp_smart_eyebrows == False:
            if vert.index in eyebrow_verts:
                continue
                
        if scn.arp_smart_nose == False:
            if vert.index in nose_verts:
                continue
                
        if scn.arp_smart_cheeks == False:
            if vert.index in cheek_verts:
                continue
                
        if scn.arp_smart_eyes == False:
            if vert.index in eye_verts:
                continue
                
        if scn.arp_smart_mouth == False:
            if vert.index in mouth_verts:
                continue
                
        if scn.arp_smart_chin == False:
            if vert.index in chin_verts:
                continue
                
        ori = source_obj.matrix_world @ vert.co
        obj_eval = depsgraph.objects.get(target_obj.name, None)
        if obj_eval:
            success, hit, normal, index = obj_eval.ray_cast(ori, ray_dir)
            
            if success == False:
                print("Vert", vert.index, "out of mesh surface, aborting")
                return False
                
            if hit:
                vert.co = source_obj.matrix_world.inverted() @ hit

    return True


def tolerance_check(source, target, axis, tolerance, x_check, side):
    if source[axis] <= target + tolerance and source[axis] >= target - tolerance:
        #left side only
        if x_check:
            if side == ".l":
                if source[0] > 0:
                    return True
            if side == ".r":
                if source[0] < 0:
                    return True
        else:
            return True


def tolerance_check_2(source, target, axis, axis2, tolerance, side):
    if source[axis] <= target[axis] + tolerance and source[axis] >= target[axis] - tolerance:
        if source[axis2] <= target[axis2] + tolerance and source[axis2] >= target[axis2] - tolerance:
            #one side only
            if side == ".l":
                if source[0] > 0:
                    return True
            if side == ".r":
                if source[0] < 0:
                    return True


def tolerance_check_3(source, target, tolerance, x_check, side):
    if source[0] <= target[0] + tolerance and source[0] >= target[0] - tolerance:
        if source[1] <= target[1] + tolerance and source[1] >= target[1] - tolerance:
            if source[2] <= target[2] + tolerance and source[2] >= target[2] - tolerance:
                #left side only
                if x_check:
                    if side == ".l":
                        if source[0] > 0:
                            return True
                    if side == ".r":
                        if source[0] < 0:
                            return True
                else:
                    return True


def clear_selection():
    bpy.ops.mesh.select_all(action='DESELECT')


def clear_object_selection():
    bpy.ops.object.select_all(action='DESELECT')
    
    
def get_facial_marker_vert_bone(vert_idx):
    for bname in ard.facial_markers:
        if ard.facial_markers[bname] == vert_idx:
            return bname
        
    
def _disable_facial_setup():
    # Hide meshes objects
    for obj in bpy.data.objects:
        if obj.type == "MESH" and obj.name != "body_temp":
            hide_object(obj)
            obj.hide_select = True
            obj["arp_smart_selection_hidden"] = True 
    
    # Reveal temp mesh object
    temp_obj = get_object("body_temp")
    if temp_obj:
        unhide_object(temp_obj)
    

    #center front view
    body_t = get_object(bpy.context.scene.arp_body_name)    
    if body_t:
        print("Center view")        
        body_t.hide_select = False
        try:
            bpy.ops.object.select_all(action='DESELECT')
        except:
            pass
        set_active_object(body_t.name)

        bpy.ops.view3d.view_axis(type='FRONT')
        try:
            bpy.ops.view3d.view_selected(use_all_regions=False)
        except:
            print("Invalid region, could not view selected")

        bpy.ops.object.select_all(action='DESELECT')
        body_t.hide_select = True
        
    set_active_object(get_object("arp_markers").children[0].name)
    
    
def _validate_facial_setup():
    hide_object(get_object('arp_facial_setup'))
    _disable_facial_setup()
    
        
def _cancel_facial_setup():
    # remove the arp_facial_setup mesh
    delete_object(get_object("arp_facial_setup"))    
    _disable_facial_setup()    


def _facial_setup():
    scn = bpy.context.scene

    # Reveal all objects for eyeballs, teeth and tongue selection
    for obj in bpy.data.objects:
        if obj.type == "MESH":
            if is_object_hidden(obj):
                unhide_object(obj)
            obj.hide_select = False

    # Hide temp mesh object
    temp_obj = get_object("body_temp")
    if temp_obj:
        hide_object(temp_obj)
    
    arp_facial_is_there = True if get_object('arp_facial_setup') else False
    
    if not arp_facial_is_there:
        # load facial object in file
        file_dir = os.path.dirname(os.path.abspath(__file__))
        addon_directory = os.path.dirname(file_dir)
        filepath = addon_directory + '/misc_presets/facial_setup.blend' 
        obj_to_load = "arp_facial_setup_no_mirror"# always load the mesh without mirror modifier then enable X-Mirror mesh editing if necessary
       
        with bpy.data.libraries.load(filepath) as (data_from, data_to):
            data_to.objects = [name for name in data_from.objects if name == obj_to_load]

        # add objects in scene
        for obj in data_to.objects:
            if obj is not None:
                scn.collection.objects.link(obj)
                if obj.name == "arp_facial_setup_no_mirror":
                    get_object("arp_facial_setup_no_mirror").name = "arp_facial_setup"# rename to final name
    
    
    bpy.ops.object.select_all(action='DESELECT')
    set_active_object('arp_facial_setup')
    obj = get_object('arp_facial_setup')
    bpy.ops.object.mode_set(mode='OBJECT')   

    # set X Mirror
    obj.data.use_mirror_x = scn.arp_smart_sym
    obj.hide_select = False

    if not arp_facial_is_there:
        # set pos and scale
        chin_loc = get_object("chin_loc")
        chin_loc_pos = None
        
        if chin_loc:# backward-compatibility
            chin_loc_pos = chin_loc.location.copy()
        else:
            chin_loc_pos = get_object("neck_loc").location.copy()
            
        obj.location[2] = chin_loc_pos[2]

        body = get_object(scn.arp_body_name)
        head_tip_loc = get_object('head_tip_loc')
        
        if scn.arp_smart_type == 'BODY':
            body_height = body.dimensions[2]            
            if head_tip_loc:
                body_height = head_tip_loc.location[2]
                
            head_height = body_height - chin_loc_pos[2]
            obj.dimensions[2] = head_height
            obj.scale = [obj.scale[2]*0.55, obj.scale[2]*0.55, obj.scale[2]*0.55]
            
        elif scn.arp_smart_type == 'FACIAL':
            body_top = body.bound_box[1][2]
            chin_z = chin_loc_pos[2]
            head_height = body_top - chin_z
            obj.dimensions[2] = head_height
            obj.scale = [obj.scale[2]*0.55, obj.scale[2]*0.55, obj.scale[2]*0.55]    
            
            if head_tip_loc == None:                            
                _add_marker('head_tip', False)
                marker_obj = get_object('head_tip_loc')
                marker_obj.location = chin_loc_pos + Vector((0, 0, head_height))
                
                bpy.ops.object.select_all(action='DESELECT')
                set_active_object('arp_facial_setup')
    
    bpy.ops.view3d.view_axis(type='FRONT')
    bpy.ops.view3d.view_selected(use_all_regions=False)    
    
    bpy.ops.object.mode_set(mode='EDIT')

    # switch to Solid mode, "In Front" is only compatible with this mode
    #  [Should not be necessary anymore. Comment out grey solid shading for now]
    #current_area = bpy.context.area
    #space_view3d = [i for i in current_area.spaces if i.type == "VIEW_3D"]
    #space_view3d[0].shading.type = 'SOLID'  


def _restore_markers():
    scene = bpy.context.scene
    print('Restore markers...')
  
    for item in scene.arp_markers_save:
        if item.name == "mirror_state":
            val = int(item.location[0])
            scene.arp_smart_sym = True if val == 1 else False
            print('Restored Mirror', val)        
    
    # Body markers
    for item in scene.arp_markers_save:
        if not '_state' in item.name:
            if not "sym_loc" in item.name:# ensure retro-compatibility, names changed
                marker_obj = get_object(item.name)
                if marker_obj == None:
                    #create it if does not exist
                    _add_marker(item.name.replace("_loc", ""), False)
                    marker_obj = get_object(item.name) 
                    
                    if marker_obj == None:
                        continue
                        
                marker_obj.location = item.location

    # Facial markers
    if len(scene.arp_facial_markers_save):
        _facial_setup()
        bpy.ops.object.editmode_toggle()#must switch to object mode to update the datas

        for item in scene.arp_facial_markers_save:
            facial_setup = get_object("arp_facial_setup")
            facial_setup.data.vertices[item.id].co = facial_setup.matrix_world.inverted() @ item.location

        bpy.ops.object.editmode_toggle()        
        
    for item in scene.arp_markers_save:      
        if item.name == "ears_state":
            val = int(item.location[0])
            scene.arp_smart_ears = True if val == 1 else False
        if item.name == 'eyebrows_state':
            val = int(item.location[0])
            scene.arp_smart_eyebrows = True if val == 1 else False
        if item.name == 'nose_state':
            val = int(item.location[0])
            scene.arp_smart_nose = True if val == 1 else False
        if item.name == 'cheek_state':
            val = int(item.location[0])
            scene.arp_smart_cheeks = True if val == 1 else False
        if item.name == 'eyes_state':
            val = int(item.location[0])
            scene.arp_smart_eyes = True if val == 1 else False
        if item.name == 'mouth_state':
            val = int(item.location[0])
            scene.arp_smart_mouth = True if val == 1 else False
        if item.name == 'tongue_state':
            val = int(item.location[0])
            scene.arp_smart_tongue = True if val == 1 else False
        if item.name == 'teeth_state':
            val = int(item.location[0])
            scene.arp_smart_teeth = True if val == 1 else False
        if item.name == 'chin_state':
            val = int(item.location[0])
            scene.arp_smart_chin = True if val == 1 else False

    #enable markers fx
    try:
        bpy.types.SpaceView3D.draw_handler_remove(handles[0], 'WINDOW')
        if bpy.context.scene.arp_debug_mode:
            print('Removed handler')
    except:
        if bpy.context.scene.arp_debug_mode:
            print('No handler to remove')
        pass
        
    bpy.ops.id.markers_fx(active=True)


def copy_list(list1, list2):
    for pikwik in range(0, len(list1)):
        list2[pikwik] = list1[pikwik]


def _turn(context, action):

    body = get_object(bpy.context.scene.arp_body_name)

    wise = 1

    if action == 'positive':
        wise = 1
    else:
        wise = -1

    bpy.ops.object.select_all(action='DESELECT')

    # restore selection visibility
    body.hide_select = False
    body_objects = []
    for obj in bpy.data.objects:
        if len(obj.keys()) > 0:
            if 'arp_body_mesh' in obj.keys():
                body_objects.append(obj)
                unhide_object(obj)
                obj.hide_select = False
                set_active_object(obj.name)
                #print('selected', obj.name)

    set_active_object(body.name)

    angle = math.pi/2*wise
  
    rotate_object(body, angle, Vector((0,0,1)), Vector((0,0,0)))
    
    for ob in body_objects:
        rotate_object(ob, angle, Vector((0,0,1)), Vector((0,0,0)))
        
    bpy.context.scene.tool_settings.transform_pivot_point = 'BOUNDING_BOX_CENTER'

    bpy.ops.object.select_all(action='DESELECT')
    set_active_object(body.name)
    
    # apply rotation
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)

    # hide from selection
    body.hide_select = True
    for obj in body_objects:
        obj.hide_select = True
        obj["arp_smart_selection_hidden"] = True
        hide_object(obj)

    set_active_object('arp_markers')
    bpy.ops.object.select_all(action='DESELECT')


def create_empty_loc(radii, pos1, name):
    bpy.ops.object.empty_add(type='PLAIN_AXES', radius = radii, location=(pos1), rotation=(0, 0, 0))
    # rename it
    bpy.context.active_object.name = name + "_auto"
    # parent it
    bpy.context.active_object.parent = get_object("auto_detect_loc")


def init_selection(active_bone):
    try:
        bpy.ops.armature.select_all(action='DESELECT')
    except:
        pass
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.pose.select_all(action='DESELECT')
    if (active_bone != "null"):
        bpy.context.active_object.data.bones.active = bpy.context.active_object.pose.bones[active_bone].bone #set the active bone for mirror
        if bpy.app.version >= (5,0,0):
            bpy.context.active_object.pose.bones[active_bone].select = True
    bpy.ops.object.mode_set(mode='EDIT')


def mirror_hack():
    revert = False
    if not bpy.context.active_object.data.use_mirror_x:
        bpy.context.active_object.data.use_mirror_x = True
        revert = True

    # Update the mirrored side, hacky
    bpy.ops.transform.translate(value=(0, 0, 0), orient_type='NORMAL')

    if revert:
        bpy.context.active_object.data.use_mirror_x = False


# OPERATOR FUNCTIONS -------------------------------------------------------------
def run_process(bin_path, img_name, threshold, fingers_amount):        
    #  Front   
    print("Running", bin_path, img_name, fingers_amount, threshold)
    args = [bin_path]
    if img_name:
        args.append(img_name)
    if fingers_amount:
        args.append(fingers_amount)
    if threshold:
        args.append(threshold)

    result = subprocess.run(args, capture_output=True, text=True)
    
    print(f"{bin_path} completed with return code {result.returncode}")
    if result.stdout:
        print(f"Output: {result.stdout}")
    if result.stderr:
        print(f"Errors: {result.stderr}")
    return result
    
    
def _fetch_facial_keypoints(self):
    print("Fetch facial keypoints...")
    
    facial_keypoints = []
    scn = bpy.context.scene
    
    for i in range(1, scn.arp_smart_AI_facial_samples+1):
        kp_path = os.path.join(self.inf_path, 'facial'+str(i)+'_kp.py')
        if os.path.exists(kp_path):# failed prediction if not
            with open(kp_path) as f:
                facial_keypoints.append(json.loads(f.readline()))    
    
    self.keypoints = facial_keypoints
    
    
def _fetch_fingers_keypoints(self, side):
    print("Fetch fingers keypoints...")
    
    for i in range(1,self.hand_idx+1):
        kp_path = os.path.join(self.inf_path, 'hand'+str(i)+side+'_kp.py')
        dict_file = {}
        
        if os.path.exists(kp_path):# failed prediction if not
            with open(kp_path) as f:
                dict_file = json.loads(f.readline())
            
        dict_name = f"dict{i}"+side
        self.keypoints[dict_name] = dict_file
 
    
def _fetch_keypoints(self):
    print("Fetch keypoints...")
    scn = bpy.context.scene
    
    # Front
    fronts_keypoints = []
    for i in range(1, scn.arp_smart_AI_body_samples+1):
        kp_path = os.path.join(self.inf_path, 'front'+str(i)+'_kp.py')
        with open(kp_path) as f:
            fronts_keypoints.append(json.loads(f.readline()))
    
    self.dicts_front = fronts_keypoints
    #print("dicts_front", dicts_front)
    
    # Side
    sides_keypoints = []
    side_samples = 1#scn.arp_smart_AI_body_samples
    for i in range(1, side_samples+1):
        kp_path = os.path.join(self.inf_path, 'side'+str(i)+'_kp.py')
        with open(kp_path) as f:
            sides_keypoints.append(json.loads(f.readline()))
    
    self.dicts_side = sides_keypoints
        
    # symmetrize dict_side
    dicts_side_copy = self.dicts_side.copy()
    
    for dict_side in dicts_side_copy:
        for n in ['shoulder', 'wrist', 'ankle', 'thigh', 'knee', 'hand_tip', 'elbow']:            
            for s in ['left_', 'right_']:            
                dict_side[s+n] = dict_side[n]
            del dict_side[n]
    
    self.dicts_side = dicts_side_copy

    # Top
    tops_keypoints = []
    top_samples = 1#scn.arp_smart_AI_body_samples
    for i in range(1, top_samples+1):
        kp_path = os.path.join(self.inf_path, 'top'+str(i)+'_kp.py')
        with open(kp_path) as f:
            tops_keypoints.append(json.loads(f.readline()))
            
    self.dicts_top = tops_keypoints


def _screenshot_cleanup(self):
    scn = bpy.context.scene
    img_list = ['char_side', 'char_top']
    
    if 'front_samples_rot' in dir(self):
        for i in range(1, scn.arp_smart_AI_body_samples+1):
            img_list.append('front'+str(i))
            
    if 'side_samples_offset' in dir(self):
        side_samples = 1#scn.arp_smart_AI_body_samples
        for i in range(1, side_samples+1):
            img_list.append('side'+str(i))
            
    if 'top_samples_rot' in dir(self):
        top_samples = 1#scn.arp_smart_AI_body_samples
        for i in range(1, top_samples+1):
            img_list.append('top'+str(i))
            
    if 'facial_samples_rot' in dir(self):
        for i in range(1, scn.arp_smart_AI_facial_samples+1):
            img_list.append('facial'+str(i))
    
    if 'hand_idx' in dir(self):
        for i in range(1, self.hand_idx+1):
            for s in ['_l', '_r']:
                img_list.append('hand'+str(i)+s)
    
    for imgname in img_list:
        img = os.path.join(self.inf_path, imgname+'.jpg')
        try:
            os.remove(img)
        except:
            pass
        
    dico_list = ['kp_side', 'kp_top', 'facial_kp']
    
    if 'hand_idx' in dir(self):
        for i in range(1, self.hand_idx+1):
            for s in ['_l', '_r']:
                dico_list.append('hand'+str(i)+s+'_kp')
                
    if 'front_samples_rot' in dir(self):        
        for i in range(1, scn.arp_smart_AI_body_samples+1):
            dico_list.append('front'+str(i)+'_kp')
            
    if 'side_samples_offset' in dir(self):
        side_samples = 1
        for i in range(1, side_samples+1):
            dico_list.append('side'+str(i)+'_kp')
            
    if 'top_samples_rot' in dir(self):
        top_samples = 1
        for i in range(1, top_samples+1):
            dico_list.append('top'+str(i)+'_kp')
            
    if 'facial_samples_rot' in dir(self):
        for i in range(1, scn.arp_smart_AI_facial_samples+1):
            dico_list.append('facial'+str(i)+'_kp')

    for diconame in dico_list:
        dico = os.path.join(self.inf_path, diconame+'.py')
        try:
            os.remove(dico)
        except:
            pass
            
            
def _set_markers_facial_from_keypoints(self):
    
    arp_facial_setup = get_object('arp_facial_setup')
    
    bpy.ops.object.mode_set(mode='OBJECT')# object mode is required when setting vertex pos
    
    ortho_scale = self.cam_ortho    
    scn = bpy.context.scene

    facial_keypoints = {
        'left_eyebrow1': 'eyebrow_01_end.l', 'left_eyebrow2': 'eyebrow_01.l', 'left_eyebrow3': 'eyebrow_02.l', 'left_eyebrow4': 'eyebrow_03.l',
        'right_eyebrow1': 'eyebrow_01_end.r', 'right_eyebrow2': 'eyebrow_01.r', 'right_eyebrow3': 'eyebrow_02.r', 'right_eyebrow4': 'eyebrow_03.r',
        'left_eyelid1': 'eyelid_corner_01.l', 'left_eyelid2': 'eyelid_top_01.l', 'left_eyelid3': 'eyelid_top_02.l', 'left_eyelid4': 'eyelid_top_03.l', 'left_eyelid5': 'eyelid_corner_02.l', 
        'left_eyelid6': 'eyelid_bot_03.l', 'left_eyelid7': 'eyelid_bot_02.l', 'left_eyelid8': 'eyelid_bot_01.l',
        'right_eyelid1': 'eyelid_corner_01.r', 'right_eyelid2': 'eyelid_top_01.r', 'right_eyelid3': 'eyelid_top_02.r', 'right_eyelid4': 'eyelid_top_03.r', 'right_eyelid5': 'eyelid_corner_02.r', 
        'right_eyelid6': 'eyelid_bot_03.r', 'right_eyelid7': 'eyelid_bot_02.r', 'right_eyelid8': 'eyelid_bot_01.r',
        'nose1': 'nose_01.x', 'nose2': 'nose_03.x',
        'left_cheek1': 'cheek_inflate.l', 'left_cheek2': 'cheek_smile.l', 
        'right_cheek1': 'cheek_inflate.r', 'right_cheek2': 'cheek_smile.r',
        'left_ear1': 'ear_01.l', 'left_ear2': 'ear_02.l', 
        'right_ear1': 'ear_01.r', 'right_ear2': 'ear_02.r',
        'lip1': 'lips_top.x', 'lip2': 'lips_top.l', 'lip3': 'lips_top_01.l', 'lip4': 'lips_smile.l', 'lip5': 'lips_bot_01.l', 'lip6': 'lips_bot.l', 'lip7': 'lips_bot.x', 
        'lip8': 'lips_bot.r', 'lip9': 'lips_bot_01.r', 'lip10': 'lips_smile.r', 'lip11': 'lips_top_01.r', 'lip12': 'lips_top.r',
        'chin1': 'chin_02.x', 'chin2': 'chin_01.x'}
    
    print('self.keypoints', self.keypoints)
    
    # Filter out invalid facial points detected    
    for dict_keypoints in self.keypoints:# 6 samples/dicts
        to_del = []
        
        for point_name in dict_keypoints:
            #print('Point name:', point_name, 'coords:', self.keypoints[point_name])
            if dict_keypoints[point_name] == None:
                feature_name = ''
                if 'eyebrow' in point_name:
                    feature_name = point_name.split('_')[0]+'eyebrow'# left_eyebrow
                elif 'eyelid' in point_name: feature_name = point_name.split('_')[0]+'eyelid'
                elif 'nose' in point_name: feature_name = 'nose'
                elif 'cheek' in point_name: feature_name = point_name.split('_')[0]+'cheek'
                elif 'ear' in point_name: feature_name = point_name.split('_')[0]+'ear'
                elif point_name.startswith('lip'): feature_name = 'lip'
                elif point_name.startswith('chin'): feature_name = 'chin'
                
                if not feature_name in to_del:
                    print('Invalid keypoint:', point_name)
                    to_del.append(feature_name)
           
        #  Disable missing facial features
        #  from invalid keypoints
        if 'left_eyebrow' in to_del and 'right_eyebrow' in to_del:
            scn.arp_smart_eyebrows = False
        if 'left_eyelid' in to_del and 'right_eyelid' in to_del:
            scn.arp_smart_eyes = False
        if 'nose' in to_del:
            scn.arp_smart_nose = False
        if 'left_cheek' in to_del and 'right_cheek' in to_del:
            scn.arp_smart_cheeks = False
        if 'left_ear' in to_del and 'right_ear' in to_del:
            scn.arp_smart_ears = False
        if 'lip' in to_del:
            scn.arp_smart_mouth = False
        if 'chin' in to_del:
            scn.arp_smart_chin = False

        #   from missing keypoints    
        for point_name in facial_keypoints:
            if point_name.startswith('left_'):# symmetricals           
                if not point_name in dict_keypoints and not 'right'+point_name[4:] in dict_keypoints:
                    print("Missing keypoint, disable facial feature:", point_name)
                    if point_name[5:].startswith('eyebrow'):
                        scn.arp_smart_eyebrows = False
                    if point_name[5:].startswith('eyelid'):
                        scn.arp_smart_eyes = False
                    if point_name[5:].startswith('cheek'):
                        scn.arp_smart_cheeks = False
                    if point_name[5:].startswith('ear'):
                        scn.arp_smart_ears = False
                        
            elif not point_name.startswith('right_'):# middles            
                if not point_name in dict_keypoints:
                    print("Missing keypoint, disable facial feature:", point_name)
                    if point_name.startswith('nose'):
                        scn.arp_smart_nose = False
                    if point_name.startswith('lip'):
                        scn.arp_smart_mouth = False
                    if point_name.startswith('chin'):
                        scn.arp_smart_chin = False
             
    bpy.ops.object.mode_set(mode='OBJECT')
    
    #   remove keypoints
    keypoints_copy = self.keypoints.copy()
    
    for dict_keypoints in keypoints_copy:
        for feature_name in to_del:
            count = 1
            if 'eyebrow' in feature_name: count = 4
            elif 'eyelid' in feature_name: count = 8
            elif 'nose' in feature_name: count = 2
            elif 'cheek' in feature_name: count = 2
            elif 'ear' in feature_name: count = 2
            elif 'lip' in feature_name: count = 12
            elif 'chin' in feature_name: count = 2
            for i in range(1, count):
                point_name = feature_name+str(i)
                if point_name in dict_keypoints:
                    print('Remove keypoint:', point_name)
                    del dict_keypoints[point_name]
                
    # For missing symmetrical facial points, force mirroring for now
    for dict_keypoints in keypoints_copy:
        missings = {}
        
        for point_name in dict_keypoints:     
            mirror_point_name = None
            if point_name.startswith('left_'):
                mirror_point_name = 'right_'+point_name[5:]
            if point_name.startswith('right_'):
                mirror_point_name = 'left_'+point_name[6:]
                
            if mirror_point_name and not mirror_point_name in dict_keypoints:
                mirror_coords = [256 - dict_keypoints[point_name][0], dict_keypoints[point_name][1]]
                missings[mirror_point_name] = mirror_coords     

        for point_name in missings:
            print("Create missing mirror point:", point_name)
            dict_keypoints[point_name] = missings[point_name]
        
    self.keypoints = keypoints_copy.copy()
    
    #   evaluate sampled positions
    print('evaluate sampled positions...')
    facial_samples_locs = {}

    for i in range(1, len(self.keypoints)+1):
        dict_facial = self.keypoints[i-1]
        roty = self.facial_samples_rot[i-1]
            
        for kp_name in dict_facial:
            #print('kp_name', kp_name, dict_facial[kp_name])
            p = dict_facial[kp_name]
            # normalize coords 0:256 > -1:1
            coords = [0,0]
            coords[0] = (p[0] - 128) / 128
            coords[1] = -(p[1] - 128) / 128# invert Y        
           
            if i == 1:# straight
                facial_samples_locs[kp_name] = [coords]            
            else:                
                # counter transforms
                #   scale
                coords[0] *= 1.05
                coords[1] *= 1.05
                #   rot
                corrected_loc = rotate_point(Vector((coords[0], 0, coords[1])), roty, Vector((0, 1, 0)), Vector((0, 0, 0)))
                coords[0], coords[1] = corrected_loc[0], corrected_loc[2]
                
                if kp_name in facial_samples_locs:
                    facial_samples_locs[kp_name].append(coords)                
                else:
                    facial_samples_locs[kp_name] = [coords]
                
      
    arp_facial_setup.location[2] = self.cams_data[0].translation[2]
    
    facial_def_locs = {}
    
    # average samples locations
    print('average locations...')
    for kp_name in facial_samples_locs:
        #print('averaging', kp_name, '...')
        sum_x = 0.0
        sum_z = 0.0
        for loc_x, loc_z in facial_samples_locs[kp_name]:
            #print('  ', round(loc_x, 2), round(loc_z, 2))
            sum_x += loc_x
            sum_z += loc_z
       
        av_loc_x = sum_x / len(facial_samples_locs[kp_name])
        av_loc_z = sum_z / len(facial_samples_locs[kp_name])
        facial_def_locs[kp_name] = (av_loc_x, av_loc_z)
        
        
    print("Extract coords...")
    for kp_name in facial_def_locs:
        #print('extracting coord:', kp_name, facial_def_locs[kp_name])
        loc_x, loc_z = facial_def_locs[kp_name]
        point_3d_coords = (Vector((loc_x, 0.0, loc_z))) * (ortho_scale*0.5) / arp_facial_setup.scale[0]
        translated_name = facial_keypoints[kp_name]
        vert_idx = ard.facial_markers[translated_name]
        vert = arp_facial_setup.data.vertices[vert_idx]
        #print("Set facial marker:", kp_name, point_3d_coords)
        vert.co[0], vert.co[2] = point_3d_coords[0], point_3d_coords[2]
        
    
    # If Mirror is enabled, compute averaged mirror coordinates
    if scn.arp_smart_sym:
        for point_name in facial_def_locs:
            left_name = None
            
            if point_name.startswith('left_'):
                left_name = point_name    
                right_name = 'right_'+left_name[5:]  

            elif point_name.startswith('lip'):
                lip_mirror_matches = {'lip2': 'lip12', 'lip3': 'lip11', 'lip4': 'lip10', 'lip5': 'lip9', 'lip6':'lip8'}
                if point_name in lip_mirror_matches:
                    left_name = point_name
                    right_name = lip_mirror_matches[left_name]
                elif point_name in ['lip1', 'lip7']:# middle lips
                    translated_name = facial_keypoints[point_name]
                    vert_idx = ard.facial_markers[translated_name]
                    vert = arp_facial_setup.data.vertices[vert_idx]
                    vert.co[0] = 0.0
                    
            if left_name:
                left_translated_name = facial_keypoints[point_name]
                left_vert_idx = ard.facial_markers[left_translated_name]
                left_vert = arp_facial_setup.data.vertices[left_vert_idx]            
                
                translated_right_name = facial_keypoints[right_name]
                right_vert_idx = ard.facial_markers[translated_right_name]
                right_vert = arp_facial_setup.data.vertices[right_vert_idx]
                
                x_avg = (abs(left_vert.co[0]) + abs(right_vert.co[0])) / 2
                y_avg = (left_vert.co[2] + right_vert.co[2]) / 2
                #print("Set facial marker:", point_name)
                left_vert.co[0], left_vert.co[2] = x_avg, y_avg
                right_vert.co[0], right_vert.co[2] = -x_avg, y_avg
                
            # mid markers
            if not point_name.startswith(('left_', 'right_', 'lip')):
                translated_name = facial_keypoints[point_name]
                vert_idx = ard.facial_markers[translated_name]
                vert = arp_facial_setup.data.vertices[vert_idx]
                vert.co[0] = 0.0
            
    
    bpy.ops.object.mode_set(mode='EDIT')
    
    print("Done.")

            
def _screenshot_facial(self):
    body_temp = get_object('body_temp')
    scn = bpy.context.scene
    facial_obj = get_object('arp_facial_setup')
    
    chin_loc = get_object('chin_loc').location.copy()
    neck_marker = get_object('neck_loc')
    neck_loc = None
    if neck_marker:
        neck_loc = neck_marker.location.copy()
        
    head_tip_loc = get_object('head_tip_loc')
    if head_tip_loc == None:
        self.report({'ERROR'}, 'Add the head tip marker first')
        return
        
    body_height = head_tip_loc.location[2]#body_temp.dimensions[2]
    head_height = body_height - chin_loc[2]
    
    margin = 1.2# if scn.sc_large_head == False else 2
    # get character dims
    bbox_corners = [body_temp.matrix_world @ Vector(corner) for corner in body_temp.bound_box]
    y1 = bbox_corners[0][1]
    y2 = bbox_corners[6][1]
    z1 = bbox_corners[0][2]
    z2 = bbox_corners[2][2]

    dim_y = abs(y2-y1)
    dim_z = abs(z2-z1)
    
    chin_loc_tip = chin_loc[2]
    if neck_loc:
        neck_length = chin_loc[2] - neck_loc[2]
        chin_loc_tip = chin_loc[2] - (neck_length * 0.3)
        
    midz = (body_height + chin_loc_tip) * 0.5
    
    # create temp camera
    curr_cam = bpy.context.scene.camera
    curr_cam_name = ''
    if curr_cam:
        curr_cam_name = curr_cam.name
        
    cam_name = 'arp_cam_head'
    cam_data = bpy.data.cameras.new(name=cam_name)
    cam_obj = bpy.data.objects.new(cam_name, cam_data)
    bpy.context.collection.objects.link(cam_obj)
    bpy.context.scene.camera = cam_obj
    cam_obj.data.type = 'ORTHO'
    cam_obj.data.ortho_scale = head_height * margin
    self.cam_ortho = cam_obj.data.ortho_scale# store value
    
    current_area = bpy.context.area
    
    # store current viewport cam
    view_matrix_copy = bpy.context.space_data.region_3d.view_matrix.copy()
    view_persp_copy = bpy.context.space_data.region_3d.view_perspective
    
    #   switch to camera view
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.region_3d.view_perspective = 'CAMERA'
                    space.use_local_camera = False
                    break
                    
    print(get_current_shading())
    use_texture = False
    
    if get_current_shading() in ['MATERIAL', 'RENDERED']:# use textures
        #cur_studio_light, theme_color, theme_gradient = switch_to_material_shading()   
        use_texture = True
    else:
        cur_shade, cur_studio_light, cur_color_type, cur_color_single, cur_light, cur_world_space_light, cur_cavity, cur_backg_type, cur_backg_color, cur_xray = switch_to_solid_shading()        
    
    curr_overlays = disable_overlays()
    cur_resolx, cur_resoly, curr_rend_perc, cur_film_transp, cur_color_space, curr_color_mode, curr_file_format, curr_media_type = set_resol(textured=use_texture)
    
    cam_obj.location = (chin_loc[0], chin_loc[1] - dim_y*10, midz)
    cam_obj.rotation_euler = [math.pi/2, 0, 0]    
    cam_obj.data.clip_end = (y2 - cam_obj.location[1]) * 2    
    
    bpy.ops.transform.translate(value=(0, 0, 0), orient_type='NORMAL')# trigger update
    
    def save_cams_data():
        self.cams_data.append(cam_obj.matrix_world.copy())
    
    
    # Samples -jitter cam rot
    picked_angles = [0]
    
    for i in range(1, scn.arp_smart_AI_facial_samples+1):
        roty = 0        
        if i == 1:
            save_cams_data()
        if i == 2:
            cam_obj.data.ortho_scale *= 1.05
        if i > 1:# first is always straight
            max_angle = 12# 15 is max
            rand_angle = random.randint(-max_angle,max_angle)
            iter = 1
            while rand_angle in picked_angles and iter < 50:# new unique angle must be picked
                rand_angle = random.randint(-max_angle,max_angle)
                
            picked_angles.append(rand_angle)
            roty = math.radians(rand_angle)
            cam_obj.rotation_euler[1] = roty
        
        self.facial_samples_rot.append(roty)
    
        # render facial screenshot
        img_name = 'facial'+str(i)+'.jpg'
        save_path = os.path.join(self.inf_path, img_name)
        bpy.ops.render.opengl(write_still=False)
        bpy.data.images['Render Result'].save_render(filepath=bpy.path.abspath(save_path))
        
    
    # delete temp cam
    bpy.data.objects.remove(cam_obj)
    
    # restore render settings
    restore_resol(cur_resolx, cur_resoly, curr_rend_perc, cur_film_transp, cur_color_space, curr_color_mode, curr_file_format, curr_media_type)
    restore_overlays(curr_overlays)
    #if use_texture:
    #    restore_shading_texture(cur_studio_light, theme_color, theme_gradient)
    #else:
    if not use_texture:
        restore_shading(cur_shade, cur_studio_light, cur_color_type, cur_color_single, cur_light, cur_world_space_light, cur_cavity, cur_backg_type, cur_backg_color, cur_xray)
    
    # restore front view
    # restore view
    bpy.context.space_data.region_3d.view_matrix = view_matrix_copy
    bpy.context.space_data.region_3d.view_perspective = view_persp_copy
    
    
def _screenshot_fingers(self, side):
    body_temp = get_object('body_temp')
    scn = bpy.context.scene
    
    set_active_object(body_temp.name)    
    
    # add subsurf modifier, better shading results for low poly meshes
    subsurf_mod = None
    if len(body_temp.data.polygons) < 6000:
        subsurf_mod = body_temp.modifiers.new('Subsurf', 'SUBSURF')        
        
    margin = 1.6
    rotate_field = 65
    rotate_field += (scn.arp_smart_AI_samples - 5) * 4# increase the rotational field as we add more samples to increase chances of better fingers visibility
    
    # setup camera according to current hand_loc and hand_tip_loc markers
    cam_name = 'arp_cam_fingers'
    cam_data = bpy.data.cameras.new(cam_name)
    cam_obj = bpy.data.objects.new(cam_name, cam_data)
    bpy.context.collection.objects.link(cam_obj)
    bpy.context.scene.camera = cam_obj
                      
    hand_loc_name = 'hand_loc' if side == '_l' else 'hand_loc_sym'
    hand_loc = get_object(hand_loc_name)
    hand_tip_loc_name = 'hand_tip_loc' if side == '_l' else 'hand_tip_loc_sym'
    hand_tip_loc = get_object(hand_tip_loc_name)
    
    hand_loc_pos = hand_loc.matrix_world.to_translation()
    hand_tip_loc_pos = hand_tip_loc.matrix_world.to_translation()
    
    hand_dir = (hand_tip_loc_pos - hand_loc_pos)
    hand_mid = (hand_tip_loc_pos + hand_loc_pos) * 0.5
    side_fac = 1 if side == '_l' else -1
    cam_pos = hand_mid + (Vector((0,-1*side_fac,0)).cross(hand_dir.normalized())).normalized() * hand_dir.magnitude
    # position
    cam_obj.location = cam_pos
    bpy.ops.transform.translate(value=(0, 0, 0))
    # orient
    cam_obj.matrix_world = lookat_up_camera(cam_obj.matrix_world, hand_mid, (Vector((0,0,1*side_fac)).cross(hand_dir.normalized())).normalized())
    # debug, zero out scale
    cam_obj.scale = [1,1,1]
    # position
    cam_obj.location = cam_pos
    
    cam_obj.data.type = 'ORTHO'
    cam_obj.data.ortho_scale = hand_dir.magnitude * margin
    self.cam_ortho = cam_obj.data.ortho_scale# store value
    cam_obj.data.clip_start = hand_dir.magnitude/100
    cam_obj.data.clip_end = hand_dir.magnitude * 100
    
    current_area = bpy.context.area
    
    # store current viewport cam
    view_matrix_copy = bpy.context.space_data.region_3d.view_matrix.copy()
    view_persp_copy = bpy.context.space_data.region_3d.view_perspective
    
    #   switch to camera view
    for space in current_area.spaces:
        if space.type == 'VIEW_3D':
            space.region_3d.view_perspective = 'CAMERA'
            break
    
    cur_shade, cur_studio_light, cur_color_type, cur_color_single, cur_light, cur_world_space_light, cur_cavity, cur_backg_type, cur_backg_color, cur_xray = switch_to_solid_shading()
    curr_overlays = disable_overlays()
    
    cur_resolx, cur_resoly, curr_rend_perc, cur_film_transp, cur_color_space, curr_color_mode, curr_file_format, curr_media_type = set_resol()    
    
    
    def save_cams_data():
        if side == '_l':
            self.cams_data_l.append(cam_obj.matrix_world.copy())
        elif side == '_r':
            self.cams_data_r.append(cam_obj.matrix_world.copy())
    
    # Render screenshots
    hand_idx = 1
    save_path = os.path.join(self.inf_path, 'hand'+str(hand_idx)+side+'.jpg')
    bpy.ops.render.opengl(write_still=False)
    bpy.data.images['Render Result'].save_render(filepath=bpy.path.abspath(save_path))
    save_cams_data()
    
    rot_angle = rotate_field/scn.arp_smart_AI_samples
    
    # forward    
    for i in range(1, scn.arp_smart_AI_samples+1):
        hand_idx += 1
        rotate_object(cam_obj, math.radians(rot_angle), get_axis(cam_obj.matrix_world, 0), hand_mid)        
        save_path = os.path.join(self.inf_path, 'hand'+str(hand_idx)+side+'.jpg')
        bpy.ops.render.opengl(write_still=False)
        bpy.data.images['Render Result'].save_render(filepath=bpy.path.abspath(save_path))
        save_cams_data()  
    
    # backward
    rotate_object(cam_obj, math.radians(-rotate_field), get_axis(cam_obj.matrix_world, 0), hand_mid)
    
    bpy.ops.transform.translate(value=(0, 0, 0), orient_type='NORMAL')# trigger update
    
    for i in range(1, scn.arp_smart_AI_samples+1):
        hand_idx += 1
        rotate_object(cam_obj, math.radians(-rot_angle), get_axis(cam_obj.matrix_world, 0), hand_mid)        
        save_path = os.path.join(self.inf_path, 'hand'+str(hand_idx)+side+'.jpg')
        bpy.ops.render.opengl(write_still=False)
        bpy.data.images['Render Result'].save_render(filepath=bpy.path.abspath(save_path))
        save_cams_data()   
    
    # delete temp cam
    bpy.data.objects.remove(cam_obj)  
    
    # restore render settings
    restore_resol(cur_resolx, cur_resoly, curr_rend_perc, cur_film_transp, cur_color_space, curr_color_mode, curr_file_format, curr_media_type)
    restore_overlays(curr_overlays)
    restore_shading(cur_shade, cur_studio_light, cur_color_type, cur_color_single, cur_light, cur_world_space_light, cur_cavity, cur_backg_type, cur_backg_color, cur_xray)
    
    # restore view
    bpy.context.space_data.region_3d.view_matrix = view_matrix_copy
    bpy.context.space_data.region_3d.view_perspective = view_persp_copy
    
    self.hand_idx = hand_idx
    
    if subsurf_mod:
        body_temp.modifiers.remove(subsurf_mod)

    
def _set_markers_fingers_from_keypoints(self, side):    
    
    def find_3d_point(mat1, mat2, p1, p2):
        p1_3d = mat1 @ (Vector((p1[0], p1[1], 0.0)) * (self.cam_ortho/2))
        p2_3d = mat2 @ (Vector((p2[0], p2[1], 0.0)) * (self.cam_ortho/2))
        d1 = get_axis(mat1, 2)
        d2 = get_axis(mat2, 2)
        solved_coords = get_closest_point_between_lines(p1_3d, d1, p2_3d, d2)
        return solved_coords
    
    scn = bpy.context.scene
    
    # Create markers
    fingers_base_list = ["thumb", "index", "middle", "ring", "pinky"]
    if scn.arp_fingers_to_detect == 4:
        fingers_base_list.remove("index")
        
    fingers_list = []
    for fname in fingers_base_list:
        for n in range(1, 5):
            fingers_list.append(fname+str(n))
    
    for marker_name in fingers_list:
        marker_obj = get_object(marker_name+'_loc')
        if marker_obj == None:
            _add_marker(marker_name, scn.arp_smart_sym)
    
    # Filter out invalid fingers detected (likely hidden)
    dicts_list = []
    for i in range(1, self.hand_idx+1):
        dicts_list.append(self.keypoints['dict'+str(i)+side])    
        
    for kp_dict in dicts_list:
        to_del = []
        for finger in kp_dict:
            if kp_dict[finger] == None:
                finger_whole_name = finger[:-1]# remove the whole finger
                if not finger_whole_name in to_del:
                    to_del.append(finger_whole_name)
                    
        for finger_name in to_del:
            for i in range(1, 5):
                if finger_name+str(i) in kp_dict:
                    del kp_dict[finger_name+str(i)]       
    
    
    # Extract 3D position from 2D matches
    # build match dict:  finger: [cam idx, coords], [cam idx, coords]...
    fingers_2d_match = {}
    print("Build 2D matches...")
    
    for fingername in fingers_list:
        data = []# cam idx, point coords
        for dico_i, dico in enumerate(dicts_list):
            if fingername in dico:
                data.append([dico_i+1, dico[fingername]])
        
        fingers_2d_match[fingername] = data
    
    # TODO: if less than 2 coords, cannot extract 3D coords
    # handle errors...
    
    # compute 3d extraction
    fingers_3d = {}
    
    def random_pairs(data):
        method = 'full'
        if method == 'full':
            all_combos = list(combinations(data, 2))
            random.shuffle(all_combos)
            return all_combos[:len(data) - 1]
            
        elif method == 'first':        
            # first coords are always first
            first = data[0]
            candidates = data[1:]
            shuffled_candidates = candidates.copy()
            random.shuffle(shuffled_candidates)
            pairs = [(first, second) for second in shuffled_candidates[:len(data) - 1]]
            return pairs
        
        
    print("Extract 3D coords...")
    for fingername in fingers_2d_match: 
        #print(fingername)
        if len(fingers_2d_match[fingername]) < 2:
            print("Cannot extract 3D coords, single coord for:", fingername)
            continue     
        
        pairs = random_pairs(fingers_2d_match[fingername])
        points_samples = []
        # evaluate pairs
        for p in pairs:
            #print("Pair:", p)
            cam1_idx = p[0][0]-1# starts from 0 in cams_data[]
            cam2_idx = p[1][0]-1
            cam1_mat = self.cams_data_l[cam1_idx] if side == '_l' else self.cams_data_r[cam1_idx]
            cam2_mat = self.cams_data_l[cam2_idx] if side == '_l' else self.cams_data_r[cam2_idx]
            
            coords1 = p[0][1]
            coords2 = p[1][1]
            # normalize coords 0:256 > -1:1
            coords1_norm = [0,0]
            coords2_norm = [0,0]
            coords1_norm[0] = (coords1[0] - 128) / 128
            coords1_norm[1] = -(coords1[1] - 128) / 128# invert Y
            coords2_norm[0] = (coords2[0] - 128) / 128
            coords2_norm[1] = -(coords2[1] - 128) / 128# invert Y
            
            point_3d = find_3d_point(cam1_mat, cam2_mat, coords1_norm, coords2_norm)
            points_samples.append(point_3d)            
        
        # Average
        #point_3d_sum = Vector((0,0,0))
        #for ps in points_samples:
        #    point_3d_sum += ps
        #point_3d_sum = point_3d_sum/len(points_samples)
        
        # Median
        point_3d_sum = np.median(points_samples, axis=0)  
        
        # Trimmed mean
        #point_3d_sum = trimmed_mean(points_samples, 0.2)
        
        fingers_3d[fingername] = point_3d_sum
        
    self.success = True
    
    for fingername in fingers_list:        
        marker_name = fingername+'_loc' if side == '_l' else fingername+'_loc_sym'
        #print('marker_name', marker_name)
        marker_obj = get_object(marker_name)
        if not fingername in fingers_3d:
            print("Finger AI detection failed:", fingername)
            self.success = False
            continue
        marker_obj.location = fingers_3d[fingername]
        
    # AI detection failed
    if not self.success:
        for fingername in fingers_list:        
            marker_name = fingername+'_loc' if side == '_l' else fingername+'_loc_sym'
            marker_obj = get_object(marker_name)
            if marker_obj:
                delete_object(marker_obj)
        
        
    else:# Refine result
        # avoid collapsed markers in the center (low error threshold)
        for fingername in fingers_list:
            marker_name = fingername+'_loc' if side == '_l' else fingername+'_loc_sym'
            hand_marker_name = 'hand_loc' if side == '_l' else 'hand_loc_sym'
            marker_obj = get_object(marker_name)
            if marker_obj.location[0] == 0.0:
                marker_obj.location[0] = get_object(hand_marker_name).location[0]
                
        
        straighten = True
        
        if straighten:
            print("Straighten...")
            # straighten
            # get hand axis
            index1_name = fingers_base_list[1]+'1_loc' if side == '_l' else fingers_base_list[1]+'1_loc_sym'#'index1_loc' if side == '_l' else 'index1_loc_sym'
            index1_loc = get_object(index1_name).location.copy()
            pinky1_name = 'pinky1_loc' if side == '_l' else 'pinky1_loc_sym'
            pinky1_loc = get_object(pinky1_name).location.copy()
            hand_axis = index1_loc - pinky1_loc
            
            
            for fingername in fingers_base_list:
                if 'thumb' in fingername:# skip thumb, can be more curled
                    continue
                    
                # get finger dir
                p1_name = fingername+'1_loc' if side == '_l' else fingername+'1_loc_sym'
                p1 = get_object(p1_name)
                p4_name = fingername+'4_loc' if side == '_l' else fingername+'4_loc_sym'
                p4 = get_object(p4_name)
                finger_dir = p4.location.copy() - p1.location.copy()
                
                # get finger normal
                hand_normal = hand_axis.cross(finger_dir)
                finger_normal = hand_normal.cross(finger_dir)
                
                for i in range(2, 4):
                    px_name= fingername+str(i)+'_loc'
                    if side == '_r':
                        px_name += '_sym'
                    px = get_object(px_name)
                    print("Straighten", px_name)
                    px.location = project_point_onto_plane(px.location, p1.location, finger_normal)
                
            
    
    print("Done.")
    
    
def _screenshot_char(self):
    body_temp = bpy.data.objects.get('body_temp')
    scn = bpy.context.scene
    
    set_active_object(body_temp.name)
    
    clear_custom_normals(body_temp)

    # get character dims
    bbox_corners = [body_temp.matrix_world @ Vector(corner) for corner in body_temp.bound_box]

    x1 = bbox_corners[0][0]
    x2 = bbox_corners[4][0]
    y1 = bbox_corners[0][1]
    y2 = bbox_corners[6][1]
    z1 = bbox_corners[0][2]
    z2 = bbox_corners[2][2]
    #print('y1', y1, 'y2', y2)
    dim_x = abs(x2-x1)
    dim_y = abs(y2-y1)
    dim_z = abs(z2-z1)
    #print(dim_x, dim_z)

    self.larger_dim = dim_x if dim_x > dim_z else dim_z
    self.larger_dimy = dim_y if dim_y > dim_z else dim_z
    self.larger_dimtop = dim_y if dim_y > dim_x else dim_x
    lower_y = y1 if y1 < y2 else y2
    greater_x = x1 if x1 > x2 else x2
    greater_z = z1 if z1 > z2 else z2
    
    self.midx = (x1+x2)*0.5
    self.midy = (y1+y2)*0.5
    self.midz = (z1+z2)*0.5
    
    # Setup screenshot settings
    # create temp camera
    cam_name = 'arp_cam_char'
    camera_data = bpy.data.cameras.new(name=cam_name)
    cam_obj = bpy.data.objects.new(cam_name, camera_data)
    bpy.context.collection.objects.link(cam_obj)
    bpy.context.scene.camera = cam_obj
    cam_obj.location = (self.midx, lower_y - dim_y*10, self.midz)
    cam_obj.rotation_euler = [math.pi/2, 0, 0]
    cam_obj.data.type = 'ORTHO'
    base_ortho_scale = self.larger_dim * self.margin
    cam_obj.data.ortho_scale = base_ortho_scale
    cam_obj.data.clip_end = 50000
    
    current_area = bpy.context.area

    cur_shade, cur_studio_light, cur_color_type, cur_color_single, cur_light, cur_world_space_light, cur_cavity, cur_backg_type, cur_backg_color, cur_xray = switch_to_solid_shading()
    curr_overlays = disable_overlays()
    cur_resolx, cur_resoly, curr_rend_perc, cur_film_transp, cur_color_space, curr_color_mode, curr_file_format, curr_media_type = set_resol()
            
    #   switch to camera view
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.region_3d.view_perspective = 'CAMERA'
                    space.use_local_camera = False
                    break
    
    
    # Render screenshots
    # front
    picked_angles = [0]
    
    for i in range(1, scn.arp_smart_AI_body_samples+1):
        img_name = 'front'+str(i)+'.jpg'
        save_path = os.path.join(self.inf_path, img_name)
        roty = 0
        # samples jitter cam rot
        if i == 2:
            cam_obj.data.ortho_scale *= 1.1
        if i != 1:# first is always straight
            max_angle = 15
            rand_angle = random.randint(-max_angle,max_angle)
            iter = 1
            while rand_angle in picked_angles and iter < 50:# new unique angle must be picked
                rand_angle = random.randint(-max_angle,max_angle)
                iter += 1
                
            picked_angles.append(rand_angle)
            roty = math.radians(rand_angle)
            cam_obj.rotation_euler[1] = roty
            
        self.front_samples_rot.append(roty)
        
        bpy.ops.render.opengl(write_still=False)
        bpy.data.images['Render Result'].save_render(filepath=bpy.path.abspath(save_path))
    
    
    # side
    picked_offsets = [0.0]
    cam_obj.location = (greater_x + dim_x*10, self.midy, self.midz)
    cam_obj.rotation_euler = [math.pi/2, 0, math.pi/2]
    cam_obj.data.ortho_scale = self.larger_dimy * self.margin
    side_samples = 1# scn.arp_smart_AI_body_samples
    
    for i in range(1, side_samples+1):
        img_name = 'side'+str(i)+'.jpg'
        save_path = os.path.join(self.inf_path, img_name)
        
        offset_y = 0.0
        # jitter cam Y
        
        if i != 1:# first is always straight
            max_offset = cam_obj.data.ortho_scale / 5
            print('max_offset', max_offset)
            rand_offset = random.uniform(-max_offset, max_offset)
            iter = 1
            while rand_offset in picked_offsets and iter < 50:# new unique offset must be picked
                rand_offset = random.uniform(-max_offset, max_offset)
                iter += 1
                
            picked_offsets.append(rand_offset)
            offset_y = rand_offset
            print('offset_y', offset_y)
            cam_obj.location[1] = self.midy + offset_y
            
        self.side_samples_offset.append(offset_y)
        
        bpy.ops.render.opengl(write_still=False)
        bpy.data.images['Render Result'].save_render(filepath=bpy.path.abspath(save_path))
        
    
    # top
    cam_obj.location = (self.midx, self.midy, greater_z + dim_z*10)
    cam_obj.rotation_euler = [0, 0, 0]
    cam_obj.data.ortho_scale = self.larger_dimtop * self.margin
    top_samples = 1# not yet implemented
    
    for i in range(1, top_samples+1):
        img_name = 'top'+str(i)+'.jpg'
        save_path = os.path.join(self.inf_path, img_name)
        self.top_samples_rot.append(0.0)
        bpy.ops.render.opengl(write_still=False)
        bpy.data.images['Render Result'].save_render(filepath=bpy.path.abspath(save_path))
    
    
    # delete temp cam
    bpy.data.objects.remove(cam_obj)
    
    # restore settings
    restore_resol(cur_resolx, cur_resoly, curr_rend_perc, cur_film_transp, cur_color_space, curr_color_mode, curr_file_format, curr_media_type)
    restore_overlays(curr_overlays)          
    restore_shading(cur_shade, cur_studio_light, cur_color_type, cur_color_single, cur_light, cur_world_space_light, cur_cavity, cur_backg_type, cur_backg_color, cur_xray)  
            
    # restore front view
    bpy.ops.view3d.view_axis(type='FRONT')
    bpy.context.space_data.region_3d.view_perspective = 'ORTHO'
    

def _set_markers_from_keypoints(self):
    scn = bpy.context.scene
    scn.arp_smart_sym = False
    
    # Create markers
    for marker_name in ['root', 'neck', 'chin', 'shoulder', 'hand', 'foot', 'thigh', 'knee', 'hand_tip', 'elbow', 'head_tip']:
        #if marker_name == 'elbow':#backward-compatibility
        #    if not 'left_elbow' in self.dicts_side:# not sure what this means, comment out for now
        #        continue
                
        marker_obj = get_object(marker_name+'_loc')
        if marker_obj == None:
            _add_marker(marker_name, False)
    
    # remap location
    x1_scaled = self.midx + (-self.larger_dim/2)*self.margin
    x2_scaled = self.midx + (self.larger_dim/2)*self.margin
    z1_scaled = self.midz + (-self.larger_dim/2)*self.margin
    z2_scaled = self.midz + (self.larger_dim/2)*self.margin
    dim_x_scaled = abs(x1_scaled-x2_scaled)
    dim_z_scaled = abs(z1_scaled-z2_scaled)
  
    ratio_x = (dim_x_scaled/256)
    ratio_z = (dim_z_scaled/256)
    
    def translate_marker_name(n):
        translated_name = n
        if 'ankle' in n:
            translated_name = n.replace('ankle', 'foot')
        elif 'wrist' in n:
            translated_name = n.replace('wrist', 'hand')
        elif 'pelvis' in n:
            translated_name = n.replace('pelvis', 'root')
        return translated_name
        
        
    def get_marker_name(n):
        marker_name = n+'_loc'      
        if kp_name.startswith('left_'):
            marker_name = n.replace('left_','')+'_loc'
        elif kp_name.startswith('right_'):
            marker_name = n.replace('right_','')+'_loc_sym'
        return marker_name
    
    # Frontal locations  
    front_samples_locs = {}
    
    #   evaluate sampled positions
    for i in range(0, scn.arp_smart_AI_body_samples):
        dict_front = self.dicts_front[i]
        roty = self.front_samples_rot[i]
            
        for kp_name in dict_front:
            #print('kp_name', kp_name, dict_front[kp_name])
            loc_x = x1_scaled + (dict_front[kp_name][0] * ratio_x)
            loc_z = z2_scaled - (dict_front[kp_name][1] * ratio_z)
            
            if i == 0:# straight
                front_samples_locs[kp_name] = [(loc_x, loc_z)]            
            else:
                # counter transforms
                #   scale
                loc_x = self.midx + (loc_x - self.midx) * 1.1
                loc_z = self.midz + (loc_z - self.midz) * 1.1
                #   rot
                corrected_loc = rotate_point(Vector((loc_x, 0, loc_z)), roty, Vector((0, 1, 0)), Vector((self.midx, 0, self.midz)))
                loc_x, loc_z = corrected_loc[0], corrected_loc[2]
                front_samples_locs[kp_name].append((loc_x, loc_z))
        
    
    #   average samples locations
    for kp_name in front_samples_locs:        
        sum_x = 0.0
        sum_z = 0.0
        for loc_x, loc_z in front_samples_locs[kp_name]:
            #print('  ', round(loc_x, 2), round(loc_z, 2))
            sum_x += loc_x
            sum_z += loc_z
       
        av_loc_x = sum_x / len(front_samples_locs[kp_name])
        av_loc_z = sum_z / len(front_samples_locs[kp_name])

        #print('  average:', round(av_loc_x, 2), round(av_loc_z, 2))
        
        # set marker
        translated_name = translate_marker_name(kp_name)
        marker_name = get_marker_name(translated_name)
        marker_obj = get_object(marker_name)
        marker_obj.location = [av_loc_x, 0.0, av_loc_z]
            
    for kp_name in front_samples_locs:
        # align vertically thighs with pelvis
        # thighs keypoints are only used for X loc
        translated_name = translate_marker_name(kp_name)
        marker_name = get_marker_name(translated_name)
        if marker_name.startswith('thigh'):
            marker_obj = get_object(marker_name)
            marker_obj.location[2] = get_object('root_loc').location[2]    
        
        
    # Side locations
    y1_scaled = self.midy + (-self.larger_dimy/2) * self.margin
    y2_scaled = self.midy + (self.larger_dimy/2) * self.margin   
    dim_y_scaled = abs(y1_scaled-y2_scaled)  
    ratio_y = (dim_y_scaled/256)
    
    z1_scaled = self.midz + (-self.larger_dimy/2) * self.margin
    z2_scaled = self.midz + (+self.larger_dimy/2) * self.margin
    dim_z_scaled = abs(z1_scaled-z2_scaled)
    ratio_z = (dim_z_scaled/256)
    
    side_samples_locs = {}
    
    #   evaluate sampled positions
    side_samples = 1# scn.arp_smart_AI_body_samples
    
    for i in range(0, side_samples):
        dict_side = self.dicts_side[i]
        offsety = self.side_samples_offset[i]
            
        for kp_name in dict_side:
            loc_y = y1_scaled + (dict_side[kp_name][0] * ratio_y)
            loc_z = z2_scaled - (dict_side[kp_name][1] * ratio_z)
            
            if i == 0:# straight
                side_samples_locs[kp_name] = [(loc_y, loc_z)]            
            else:
                # counter transforms
                loc_y = loc_y + offsety
                side_samples_locs[kp_name].append((loc_y, loc_z))
        
        
    #   average samples locations
    for kp_name in side_samples_locs:        
        sum_y = 0.0
        sum_z = 0.0
        for loc_y, loc_z in side_samples_locs[kp_name]:
            sum_y += loc_y
            sum_z += loc_z
        
        av_loc_y = sum_y / len(side_samples_locs[kp_name])
        av_loc_z = sum_z / len(side_samples_locs[kp_name])
        
        # set marker
        translated_name = translate_marker_name(kp_name)
        marker_name = get_marker_name(translated_name)
        marker_obj = get_object(marker_name)
        marker_obj.location[1] = av_loc_y
        
        # Average with front Z    
        if kp_name in ['head_tip', 'knee', 'ankle']:# or 'pelvis' in kp_name or 'thigh' in kp_name:
            front_z = marker_obj.location[2]
            marker_obj.location[2] = (front_z + av_loc_z) * 0.5
            #print("Average", kp_name, "Z. Before:", front_z, "After:", marker_obj.location[2])          
        
        '''
        # force knee in the middle
        # comment out for now, should not be necessary anymore with the latest refined model files, 
        # and is more prone to error since knees are not always perfectly mid distance
        if 'knee' in kp_name:
            marker_thigh = get_object('thigh_loc')
            marker_thigh_z = marker_thigh.location[2]
            marker_foot = get_object('foot_loc')
            marker_foot_z = marker_foot.location[2]
            marker_obj.location[2] = (marker_thigh_z + marker_foot_z) * 0.5
        '''
            
    bpy.ops.transform.translate(value=(0, 0, 0), orient_type='NORMAL')# trigger update
    
    # get arm angle
    shoulder_loc = get_object('shoulder_loc').matrix_world.to_translation()
    hand_loc = get_object('hand_loc').matrix_world.to_translation()
    arm_angle = (shoulder_loc - hand_loc).angle(Vector((0,0,1)))
    arm_angle = math.degrees(arm_angle)
    print('Arm angle:', round(arm_angle, 2))
    
    
    # Top locations
    x1_scaled = self.midx + (-self.larger_dimtop/2)*self.margin
    x2_scaled = self.midx + (self.larger_dimtop/2)*self.margin
    dim_x_scaled = abs(x1_scaled-x2_scaled)
    ratio_x = (dim_x_scaled/256)
    y1_scaled = self.midy + (-self.larger_dimtop/2)*self.margin
    y2_scaled = self.midy + (self.larger_dimtop/2)*self.margin   
    dim_y_scaled = abs(y1_scaled-y2_scaled)  
    ratio_y = (dim_y_scaled/256)
    
    
    if arm_angle > 20:# skip top evaluation if vertical arms
        
        # evaluate sampled positions
        top_samples_locs = {}
        top_samples = 1# scn.arp_smart_AI_body_samples
        
        for i in range(0, top_samples):
            dict_top = self.dicts_top[i]
            roty = self.top_samples_rot[i]
                
            for kp_name in dict_top:
                if dict_top[kp_name] == None or -1 in dict_top[kp_name]:
                    print('Top predict failed:', kp_name)
                    continue
                
                loc_x = x1_scaled + (dict_top[kp_name][0] * ratio_x)
                loc_y = y2_scaled - (dict_top[kp_name][1] * ratio_y)
              
                if i == 0:# straight
                    top_samples_locs[kp_name] = [(loc_x, loc_y)]            
                else:# not yet implemented
                    # counter transforms
                    #   scale
                    loc_x = self.midx + (loc_x - self.midx) * 1.1
                    loc_y = self.midy + (loc_y - self.midy) * 1.1
                    #   rot
                    corrected_loc = rotate_point(Vector((loc_x, loc_y, 0.0)), roty, Vector((0, 0, 1)), Vector((self.midx, self.midy, 0)))
                    loc_x, loc_y = corrected_loc[0], corrected_loc[1]
                    top_samples_locs[kp_name].append((loc_x, loc_y))
                
        
        # average samples locations
        for kp_name in top_samples_locs:        
            sum_x = 0.0
            sum_y = 0.0
            for loc_x, loc_y in top_samples_locs[kp_name]:
                sum_x += loc_x
                sum_y += loc_y
            
            av_loc_x = sum_x / len(top_samples_locs[kp_name])
            av_loc_y = sum_y / len(top_samples_locs[kp_name])
            
            # set marker
            translated_name = translate_marker_name(kp_name)
            marker_name = get_marker_name(translated_name)
            marker_obj = get_object(marker_name)
            
            marker_obj.location[1] = av_loc_y
            
            # average X with front view
            if kp_name in ['wrist', 'hand_tip', 'elbow']:
                marker_obj.location[0] = (marker_obj.location[0] + av_loc_x) * 0.5
            
            # average Y with side view
            marker_obj.location[1] = (marker_obj.location[1] + av_loc_y) * 0.5    
           
           
    # --Refine result --
    
    # Avoid inverted knee (may lead to offset the knee out of the mesh though -blame the character design not complying with IK constraints
    # Note: The knee is automatically corrected in match_ref() too. 
    # but this initial correction makes the knee closer to its final position for a better preview,
    # and the thigh joint is adjusted too, mitigating the problem
    for side in ['.l']:# TODO asymmetrical support
        suff = '' if side == '.l' else '_sym'
        thigh_marker = get_object('thigh_loc'+suff)
        foot_marker = get_object('foot_loc'+suff)
        knee_marker = get_object('knee_loc'+suff)
        
        leg_mid = (thigh_marker.location + foot_marker.location) / 2
        
        if leg_mid[1] < knee_marker.location[1]:
            print("Inverted knee, fix...", leg_mid)
            safe_offset = (knee_marker.location - thigh_marker.location).magnitude * 0.05
            correc_vec = (leg_mid[1]-knee_marker.location[1])
            
            # first try to apply the fix to both thigh and knee
            thigh_marker.location[1] -= (correc_vec - safe_offset*0.5) * 0.5
            knee_marker.location[1] += (correc_vec - safe_offset*0.5) * 0.5
            
            leg_mid = (thigh_marker.location + foot_marker.location) / 2
            
            # if still inverted, tweak the knee only
            if leg_mid[1] < knee_marker.location[1]:                
                print("  second fix", leg_mid)
                correc_vec = (leg_mid[1]-knee_marker.location[1])
                knee_marker.location[1] += correc_vec - safe_offset
        
        
    
    # Wrist: ensure it's inside the mesh, to fix precision issues
    body_temp = get_object('body_temp')
    depsgraph = bpy.context.evaluated_depsgraph_get()
    obj_eval = depsgraph.objects.get(body_temp.name, None)
    body_depth = body_temp.dimensions[1]    
    
    for side in ['.l']:# TODO asymmetrical support
        suff = '' if side == '.l' else '_sym'
        success = False
        rotate_dir = 1
        trials = 0
        max_trials = 40
        
        hand_marker = get_object('hand_loc'+suff)
        shoulder_marker = get_object('shoulder_loc'+suff)
        hand_marker_backup = hand_marker.location.copy()
        
        wrist_invalid = False
        wrist_fixed = False
        
        while success == False:
            ray_origin = hand_marker.location + vectorize3([0, -body_depth*5, 0])
            ray_dir = vectorize3([0, body_depth*50, 0])
            success, hit, normal, index = obj_eval.ray_cast(ray_origin, ray_dir)

            if success == False:
                wrist_invalid = True
                if trials > max_trials:
                    if rotate_dir == 1:
                        trials = 0
                        rotate_dir = -1
                        hand_marker.location = hand_marker_backup
                    else:                        
                        hand_marker.location = hand_marker_backup
                        break
                    
                # rotate                
                hand_marker.location = rotate_point(hand_marker.location, math.radians(0.5)*rotate_dir, Vector((0,1,0)), shoulder_marker.location)
                trials += 1
                
            else:# fixed
                if wrist_invalid:
                    wrist_fixed = True                
            
                
        if wrist_invalid:
            print("Wrist marker was invalid. Fixing trials:", trials, 'Dir', rotate_dir)
            if wrist_fixed:
                wloc = [round(hand_marker.location[0],3), round(hand_marker.location[1], 3), round(hand_marker.location[2], 3)]
                print("Fixed. New wrist loc:", wloc)
            else:
                print("Could not fix the wrist marker, restore to original location")
                
                
    # Ankle: ensure it's inside the mesh, to fix precision issues 
    for side in ['.l']:# TODO asymmetrical support
        suff = '' if side == '.l' else '_sym'
        success = False
        rotate_dir = 1
        trials = 0
        max_trials = 40
        
        foot_marker = get_object('foot_loc'+suff)
        thigh_marker = get_object('thigh_loc'+suff)
        foot_marker_backup = foot_marker.location.copy()
        
        foot_invalid = False
        foot_fixed = False
        
        while success == False:
            ray_origin = foot_marker.location + vectorize3([0, -body_depth*5, 0])
            ray_dir = vectorize3([0, body_depth*50, 0])
            success, hit, normal, index = obj_eval.ray_cast(ray_origin, ray_dir)

            if success == False:
                foot_invalid = True
                if trials > max_trials:
                    if rotate_dir == 1:
                        trials = 0
                        rotate_dir = -1
                        foot_marker.location = foot_marker_backup
                    else:                        
                        foot_marker.location = foot_marker_backup
                        break
                    
                # rotate                
                foot_marker.location = rotate_point(foot_marker.location, -math.radians(0.5)*rotate_dir, Vector((0,1,0)), thigh_marker.location)
                trials += 1
                
            else:# fixed
                if foot_invalid:
                    foot_fixed = True                
            
                
        if foot_invalid:
            print("Foot marker was invalid. Fixing trials:", trials, 'Dir', rotate_dir)
            if foot_fixed:
                wloc = [round(foot_marker.location[0],3), round(foot_marker.location[1], 3), round(foot_marker.location[2], 3)]
                print("Fixed. New foot loc:", wloc)
            else:
                print("Could not fix the foot marker, restore to original location")
        
                
    
    # enable markers fx
    cleanup(None)        
    bpy.ops.id.markers_fx(active=True)
    

def _match_ref(self):

    print('\nMatching the reference bones...')

    scn = bpy.context.scene
    b_name = scn.arp_body_name
    body = get_object(b_name)
    rig_name = self.overwritten_rig
    rig = get_object(rig_name)  
    found_picker = False

    # Unparent first meshes from the armature if any
    if len(rig.children):
        for child in rig.children:
            if "rig_ui" in child.name and child.type == "EMPTY":
                found_picker = True
            if child.type == "MESH":
                child_mat = child.matrix_world.copy()
                child.parent = None
                # keep transforms
                child.matrix_world = child_mat


    # scale the rig object according to the character height
    fac = 1
    if found_picker:
        fac = 35
    
    arp_facial_setup = get_object("arp_facial_setup")
    
    if scn.arp_smart_type == 'FACIAL':
        if self.rig_added == True:# existing rigs (from Quick Rig or other) scale should not be modified
            #rig.dimensions[2] = get_object("head_loc_auto").location[2] * fac#body.dimensions[2] * fac    
            if arp_facial_setup:
                # set global scale according to distance between left and right eyes
                eyel_l_loc = arp_facial_setup.matrix_world @ arp_facial_setup.data.vertices[ard.facial_markers['eyelid_corner_01.l']].co
                eyel_r_loc = arp_facial_setup.matrix_world @ arp_facial_setup.data.vertices[ard.facial_markers['eyelid_corner_01.r']].co
                eye_dist = (eyel_l_loc-eyel_r_loc).magnitude
                rig.dimensions[2] = eye_dist * 60
                
    elif scn.arp_smart_type == 'BODY':
        rig.dimensions[2] = body.dimensions[2] * fac
        
    rig.scale[1] = rig.scale[2]
    rig.scale[0] = rig.scale[2]

    
    # Apply the facial markers modifiers if any
    print("    Applying the facial if any...")
    
    if arp_facial_setup:
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        arp_facial_setup.hide_select = False
        set_active_object("arp_facial_setup")
        
        arp_facial_setup.location[1] += -get_object(b_name).dimensions[1] * 40

        # make planar
        for vert in arp_facial_setup.data.vertices:
            vert.co[1] = 0.0

        # add shrinkwrap mod
        if len(arp_facial_setup.modifiers) > 0:
            arp_facial_setup.modifiers.remove(arp_facial_setup.modifiers[0])
        mod = arp_facial_setup.modifiers.new('shrinkwrap', 'SHRINKWRAP')
        mod.target = get_object(b_name)
        mod.wrap_method = 'PROJECT'
        mod.use_project_x = False
        mod.use_project_y = True
        mod.use_project_z = False
        mod.use_positive_direction = True
        mod.use_negative_direction = False

        bpy.ops.object.convert(target='MESH')
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # Eyeball loc
        if scn.arp_smart_eyes:
            eyeb1 = get_object(scn.arp_eyeball_name)
            unhide_object(eyeb1)
            set_active_object(eyeb1.name)

            bpy.ops.object.mode_set(mode='EDIT')

            #   make sure to unhide all verts
            bpy.ops.mesh.reveal()
            bpy.ops.mesh.select_all(action='DESELECT')

            #   find the vert the more on the left
            left_vert = None
            _mesh = bmesh.from_edit_mesh(eyeb1.data)
            for vert in _mesh.verts:
                if left_vert == None:
                    left_vert = vert
                else:
                    if vert.co[0] > left_vert.co[0]:
                        left_vert = vert
                        
            #   for hemispheres, find the back vert
            back_left_vert = None
            if scn.arp_smart_eye_shape == 'HEMISPHERE':            
                back_left_vert = None
                for vert in _mesh.verts:
                    if back_left_vert == None:
                        back_left_vert = vert
                    else:
                        if vert.co[1] > back_left_vert.co[1]:
                            back_left_vert = vert

            left_vert.select = True
            bpy.ops.mesh.select_linked(delimit=set())
            scn.tool_settings.transform_pivot_point = 'BOUNDING_BOX_CENTER'
            bpy.ops.view3d.snap_cursor_to_selected()
            
            if scn.arp_smart_eye_shape == 'HEMISPHERE': 
                scn.cursor.location[1] = (eyeb1.matrix_world @  back_left_vert.co)[1]
                
            eyeball_loc = scn.cursor.location.copy()

            bpy.ops.object.mode_set(mode='OBJECT')
            hide_object(eyeb1)


            eyeball_loc_right = None

            if scn.arp_eyeball_type == 'SEPARATE' and scn.arp_smart_sym == False:# right eyeball if set, non-mirror mode
                eyeb2 = get_object(scn.arp_eyeball_name_right)
                unhide_object(eyeb2)
                bpy.ops.object.select_all(action='DESELECT')
                set_active_object(eyeb2.name)

                bpy.ops.object.mode_set(mode='EDIT')

                # make sure to unhide all verts
                bpy.ops.mesh.reveal()
                bpy.ops.mesh.select_all(action='DESELECT')

                #find the vert the more on the right
                right_vert = None
                _mesh = bmesh.from_edit_mesh(eyeb2.data)
                for vert in _mesh.verts:
                    if right_vert == None:
                        right_vert = vert
                    else:
                        if vert.co[0] < right_vert.co[0]:
                            right_vert = vert
                            
                #   for hemispheres, find the back vert
                back_right_vert = None
                if scn.arp_smart_eye_shape == 'HEMISPHERE':            
                    back_right_vert = None
                    for vert in _mesh.verts:
                        if back_right_vert == None:
                            back_right_vert = vert
                        else:
                            if vert.co[1] > back_right_vert.co[1]:
                                back_right_vert = vert

                right_vert.select = True
                bpy.ops.mesh.select_linked(delimit=set())
                scn.tool_settings.transform_pivot_point = 'BOUNDING_BOX_CENTER'
                bpy.ops.view3d.snap_cursor_to_selected()
                
                if scn.arp_smart_eye_shape == 'HEMISPHERE': 
                    scn.cursor.location[1] = (eyeb2.matrix_world @ back_right_vert.co)[1]

                eyeball_loc_right = scn.cursor.location.copy()

                bpy.ops.object.mode_set(mode='OBJECT')

        set_active_object(rig_name)


    # Start matching the bones coords to auto_loc coords
    bpy.ops.object.mode_set(mode='EDIT')
    

    # display all layers    
    _layers = enable_all_armature_layers()
    
    sides = [".l", ".r"]
    side = ".l"

    rig_matrix_world_inv = get_object(rig_name).matrix_world.inverted()
    rig_matrix = get_object(rig_name).matrix_world

    used_sides = [".l"]

    # enable x-axis mirror edit or not
    if scn.arp_smart_sym:
        rig.data.use_mirror_x = True
    else:
        rig.data.use_mirror_x = False
        used_sides.append(".r")

        
    # save the chin loc position to use with the "Use Chin" binding option
    chin_loc = get_object("chin_loc")
    bpy.context.active_object.data["arp_chin_loc"] = chin_loc.location[2]
    bpy.context.active_object.data['arp_chin_pos_vec'] = chin_loc.location.copy()
    print('    arp_chin_pos_vec',chin_loc.location)
    
    if scn.arp_smart_type == 'FACIAL':
        head_ref = get_edit_bone("head_ref.x")
        head_ref.head = rig_matrix_world_inv @ get_object("head_loc_auto").location
        head_ref.tail = rig_matrix_world_inv @ get_object("head_end_loc_auto").location
        
        neck_ref = get_edit_bone("neck_ref.x")
        head_vec = head_ref.tail - head_ref.head
        neck_ref.head = head_ref.head - (head_vec * 0.25)
        
    
    if scn.arp_smart_type == 'BODY':
        for used_side in used_sides:
            # Feet
            print("\n    matching feet", used_side, "...")
            
            #init_selection('foot_ref'+used_side)
            foot = get_edit_bone("foot_ref"+used_side)
            foot.head = rig_matrix_world_inv @ get_object('ankle_loc'+used_side+'_auto').location
            foot.tail = rig_matrix_world_inv @ get_object('toes_start'+used_side+'_auto').location
            align_bone_z_axis(foot, Vector((0,0,1)))
            #bpy.ops.armature.calculate_roll(type='GLOBAL_POS_Z')
            
            if scn.arp_smart_sym:
                mirror_hack()

            #init_selection('toes_ref'+used_side)
            toes_ref = get_edit_bone('toes_ref'+used_side)
            toes_ref.head = rig_matrix_world_inv @ get_object('toes_start'+used_side+'_auto').location
            toes_ref.tail = rig_matrix_world_inv @ get_object('toes_end'+used_side+'_auto').location
            align_bone_z_axis(toes_ref, Vector((0,0,1)))
            #bpy.ops.armature.calculate_roll(type='GLOBAL_POS_Z')
            
            if scn.arp_smart_sym:
                mirror_hack()


            foot_dir = scn.arp_foot_dir_l
            if used_side == ".r":
                foot_dir = scn.arp_foot_dir_r

            init_selection('foot_bank_01_ref'+used_side)
            foot_bank_01_ref = get_edit_bone('foot_bank_01_ref'+used_side)
            bank_right = get_object('bank_left_loc'+used_side+'_auto').location
            
            foot_bank_01_ref.head = rig_matrix_world_inv @ bank_right
            foot_bank_01_ref.tail = foot_bank_01_ref.head + (foot_dir.normalized() * get_edit_bone('foot_ref'+used_side).length*0.2)
            
            if scn.arp_smart_sym:
                mirror_hack()

            init_selection("foot_bank_02_ref"+used_side)
            foot_bank_02_ref = get_edit_bone("foot_bank_02_ref"+used_side)
            bank_left = get_object("bank_right_loc" + used_side +"_auto").location
            foot_bank_02_ref.head = rig_matrix_world_inv @ bank_left
            foot_bank_02_ref.tail = foot_bank_02_ref.head + (foot_dir.normalized() * get_edit_bone('foot_ref'+used_side).length*0.2)

            if scn.arp_smart_sym:
                mirror_hack()

            init_selection("foot_heel_ref"+used_side)
            foot_heel_ref = get_edit_bone("foot_heel_ref"+used_side)
            heel_auto = get_object("bank_mid_loc" + used_side + "_auto").location
            foot_heel_ref.head = rig_matrix_world_inv @ heel_auto
            foot_heel_ref.tail = foot_heel_ref.head + (foot_dir.normalized() * get_edit_bone('foot_ref'+used_side).length*0.2)
            if scn.arp_smart_sym:
                mirror_hack()

            toes_end_auto = get_object("toes_end" + used_side + "_auto").location
            heel_auto = get_object("bank_mid_loc" + used_side + "_auto").location
            foot_length = (toes_end_auto - heel_auto).magnitude

            if scn.arp_smart_sym:
                bpy.context.active_object.data.use_mirror_x = True


            # Legs
            print("    matching legs", used_side, "...")
            
            init_selection("thigh_ref"+used_side)
            thigh_ref = get_edit_bone("thigh_ref"+used_side)
            leg_ref = get_edit_bone("leg_ref"+used_side)
            knee_auto = get_object("knee_loc" + used_side + "_auto").location
            thigh_ref.tail = rig_matrix_world_inv @ knee_auto
            thigh_ref.head = rig_matrix_world_inv @ get_object("leg_loc" + used_side + "_auto").location

            #   make sure the knee is pointing forward for IK
            foot_ref = get_edit_bone("foot_ref" + used_side)
            midpoint = (foot_ref.head + thigh_ref.head)*0.5

            if scn.arp_debug_mode:
                print("    Knee median point:", midpoint[1])
                print("    Current thigh tail:",  thigh_ref.tail[1])

            if thigh_ref.tail[1] > midpoint[1]:
                print("    The knee is pointing backward, change that...")
                print("    Old:", thigh_ref.tail[1])
             
                # auto-align knee position with global Y axis to ensure IK pole vector is physically correct
                leg_axis = leg_ref.tail - thigh_ref.head
                leg_midpoint = (thigh_ref.head + leg_ref.tail) * 0.5
                cur_vec = leg_ref.head - leg_midpoint
                cur_vec[2] = 0.0
                global_y_vec = Vector((0, -1, 0))
                signed_cur_angle = signed_angle(cur_vec, global_y_vec, leg_axis)
                print("    IK correc angle:", degrees(signed_cur_angle))
                
                offset_vec = -leg_midpoint
                offset_knee = leg_ref.head + offset_vec
                # rotate in world origin space
                rot_mat = Matrix.Rotation(-signed_cur_angle, 4, leg_axis.normalized())
                knee_rotated = rot_mat @ offset_knee
                # bring back to original space
                knee_rotated = knee_rotated -offset_vec                
                
                thigh_ref.tail = knee_rotated
                print("    New:", thigh_ref.tail[1])

            # auto-align the knee based on the foot direction for more in line rotation
            auto_align_knee = True
            if auto_align_knee:
                toes_ref = get_edit_bone("toes_ref"+used_side)
                thigh_ref.tail = project_point_onto_plane(thigh_ref.tail, thigh_ref.head, (toes_ref.tail-foot_ref.head).cross(toes_ref.tail-thigh_ref.head))

            if scn.arp_smart_sym:
                mirror_hack()
                
            #   roll
            init_selection("leg_ref"+used_side)
            bpy.ops.armature.calculate_roll(type='POS_Z')
            thigh_ref = get_edit_bone("thigh_ref"+used_side)
            leg_ref = get_edit_bone("leg_ref"+used_side)
            align_bone_x_axis(thigh_ref, leg_ref.x_axis)
            
            if used_side.endswith(".r"):
                leg_ref.roll += radians(-180)
                thigh_ref.roll += radians(-180)
            
            
            if get_edit_bone("bot_bend_ref" + used_side):
                init_selection("bot_bend_ref"+used_side)
                bot_bend_ref = get_edit_bone("bot_bend_ref"+used_side)
                bot_auto = get_object("bot_empty_loc" + used_side + "_auto").location
                bot_bend_ref.head = rig_matrix_world_inv @ bot_auto

                bot_bend_ref.tail = bot_bend_ref.head + (rig_matrix_world_inv @ vectorize3([0, foot_length/4, 0]))

                if scn.arp_smart_sym:
                    mirror_hack()

                if used_side == ".l":# one side only affect both
                    #disable it by default
                    auto_rig._disable_limb(self, bpy.context)


        # Spine
        print("\n    matching spine...")        
        spine_count = 3
        root_ref = get_data_bone('root_ref.x')
        if root_ref:
            spine_count = root_ref['spine_count']
        
        if spine_count != 3:
            select_edit_bone(root_ref.name, mode=1)
            auto_rig.set_spine(count=3, grid_align=True, bottom=False)
        
        root_ref = get_edit_bone("root_ref.x")
        root_auto = get_object("root_loc_auto").location
        root_ref.head = rig_matrix_world_inv @ root_auto
        root_ref.tail = rig_matrix_world_inv @ get_object("spine_01_loc_auto").location
        
        spine_01_ref = get_edit_bone("spine_01_ref.x")
        spine_01_ref.tail = rig_matrix_world_inv @ get_object("spine_02_loc_auto").location
        
        spine_02_ref = get_edit_bone("spine_02_ref.x")
        spine_02_ref.tail = rig_matrix_world_inv @ get_object("neck_loc_auto").location
        
        neck_ref = get_edit_bone("neck_ref.x")
        neck_ref.head = rig_matrix_world_inv @ get_object("neck_loc_auto").location
        neck_ref.tail = rig_matrix_world_inv @ get_object("head_loc_auto").location
        
        head_ref = get_edit_bone("head_ref.x")
        head_ref.tail = rig_matrix_world_inv @ get_object("head_end_loc_auto").location

        
        for used_side in used_sides:
            used_marker_side = '' if used_side == '.l' else '_sym'
            # Arms
            print("\n    matching arms", used_side, "...")            
            
            #   shoulder
            init_selection("shoulder_ref"+used_side)
            shoulder_ref = get_edit_bone("shoulder_ref"+used_side)
            shoulder_ref.head = rig_matrix_world_inv @ get_object("shoulder_base_loc" + used_side + "_auto").location
            shoulder_ref.tail = rig_matrix_world_inv @ get_object("shoulder_loc" + used_side + "_auto").location
            if scn.arp_smart_sym:
                mirror_hack()

            #   arm
            init_selection("arm_ref"+used_side)
            arm_ref = get_edit_bone("arm_ref"+used_side)
            arm_ref.tail = rig_matrix_world_inv @ get_object("elbow_loc"+used_side+"_auto").location
            if scn.arp_smart_sym:
                mirror_hack()

            #   forearm
            init_selection("forearm_ref"+used_side)
            forearm_ref = get_edit_bone("forearm_ref"+used_side)
            forearm_ref.tail = rig_matrix_world_inv @ get_object("hand_loc"+used_side+"_auto").location
            if scn.arp_smart_sym:
                mirror_hack()
            
            #   make sure the elbow is pointing backward for IK
            arm_ref = get_edit_bone("arm_ref"+used_side)
            midpoint = (arm_ref.head + forearm_ref.tail) * 0.5
            #print("forearm_ref.head", forearm_ref.head[1])
            #print("midpoint", midpoint)
            
            if forearm_ref.head[1] < midpoint[1]:
                print("    The elbow is pointing forward, change that...")
                print("    Old:", forearm_ref.head[1])
             
                # auto-align elbow position with global Y axis to ensure IK pole vector is physically correct
                arm_axis = forearm_ref.tail - arm_ref.head
                cur_vec = forearm_ref.head - midpoint
                cur_vec[2] = 0.0
                global_y_vec = Vector((0, 1, 0))
                signed_cur_angle = signed_angle(cur_vec, global_y_vec, arm_axis)
                print("    IK correc angle:", degrees(signed_cur_angle))                
                
                offset_elbow = forearm_ref.head - midpoint
                # rotate in world origin space
                rot_mat = Matrix.Rotation(signed_cur_angle, 4, arm_axis.normalized())
                elbow_rotated = rot_mat @ offset_elbow
                # bring back to original space
                offset_vec = -midpoint
                elbow_rotated = elbow_rotated -offset_vec
                
                # apply the correction to both the elbow (-Y) and arm (+Y) to improve the result
                forearm_ref.head = elbow_rotated
                print("    New:", forearm_ref.head[1])
                
            if scn.arp_smart_sym:
                mirror_hack()
                
            #   roll
            init_selection("forearm_ref"+used_side)
            bpy.ops.armature.calculate_roll(type='NEG_Z')
            
            arm_ref = get_edit_bone("arm_ref"+used_side)
            forearm_ref = get_edit_bone("forearm_ref"+used_side)
            align_bone_x_axis(arm_ref, forearm_ref.x_axis)
            
            if used_side.endswith(".r"):
                arm_ref.roll += radians(-180)
                forearm_ref.roll += radians(-180)
            
            #   hand
            init_selection("hand_ref"+used_side)
            hand_ref = get_edit_bone("hand_ref"+used_side)

            #   check if fingers are detected
            middle_pos = None
            if scn.arp_fingers_to_detect != 0:
                auto_name = "middle_bot"+used_side+"_auto"
                marker_name = "middle1_loc"+used_marker_side
                
                if get_object(auto_name):
                    middle_pos = get_object(auto_name)                
                elif get_object(marker_name):
                    middle_pos = get_object(marker_name)
                
            if middle_pos:
                hand_ref.tail = hand_ref.head + (rig_matrix_world_inv @ middle_pos.location - hand_ref.head)*0.6
            else:
                forearm_ref = get_edit_bone("forearm_ref"+used_side)
                hand_ref.tail = hand_ref.head + ((forearm_ref.tail - forearm_ref.head)/3)

            #   hand roll
            #   get hand/x-axis angle
            hand_vec = hand_ref.y_axis
            hand_vec[1] = 0


            # get the hand "normal" according to the pinky/index roots and place the cursor above to calculate the hand roll
            left_pos = None
            right_pos = None

            if get_object("pinky_root"+used_side+"_auto"):
                left_pos = get_object("pinky_root"+used_side+"_auto").location.copy()
            elif get_object("ring_root"+used_side+"_auto"):
                left_pos = get_object("ring_root"+used_side+"_auto").location.copy()
            elif get_object("pinky1_loc"+used_marker_side):
                left_pos = get_object("pinky1_loc"+used_marker_side).location.copy()

            if get_object("index_root"+used_side+"_auto"):
                right_pos = get_object("index_root"+used_side+"_auto").location
            elif get_object("index1_loc"+used_marker_side):
                right_pos = get_object("index1_loc"+used_marker_side).location.copy()

            if left_pos and right_pos:
                hand_loc = get_object("hand_loc"+used_side+"_auto").location
                hand_normal = cross(left_pos-right_pos, hand_loc-right_pos).normalized()
                if (used_side == ".r"):
                    hand_normal *= -1
                cursor_loc = hand_loc + vectorize3(hand_normal) * bpy.context.active_object.dimensions[0]
                scn.cursor.location = cursor_loc
                bpy.ops.armature.calculate_roll(type='CURSOR')

            else:
                bpy.ops.armature.calculate_roll(type='GLOBAL_POS_Z')


            if scn.arp_smart_sym:
                mirror_hack()


            # FINGERS --------------------------------------------
            print("    matching fingers", used_side, "...")

            select_hands= ['hand_ref'+used_side]
            if len(used_sides) == 1:# set opposite side too if mirror is enabled
                select_hands.append('hand_ref.r')

            for hname in select_hands:
                # setting fingers is based on the current selected bone
                init_selection(hname)
                
                if scn.arp_fingers_enable == False:
                    auto_rig.set_fingers(False, False, False, False, False)
                      
                if scn.arp_fingers_to_detect == 1:
                    auto_rig.set_fingers(False, True, False, False, False)
               
                elif scn.arp_fingers_to_detect == 2:
                    auto_rig.set_fingers(True, True, False, False, False)
              
                elif scn.arp_fingers_to_detect == 3:
                    auto_rig.set_fingers(True, False, False, True, True)

                # If fingers to detect is set to 4, enable all fingers but pinky
                elif scn.arp_fingers_to_detect == 4:
                    auto_rig.set_fingers(True, False, True, True, True)
              
                elif scn.arp_fingers_to_detect == 5:
                    auto_rig.set_fingers(True, True, True, True, True)


            # make list of fingers bones
            finger_bones = []
            init_selection("hand_ref"+used_side)
            bpy.ops.armature.select_similar(type='CHILDREN')

            for bone in bpy.context.active_object.data.edit_bones:
                if bone.select and bone.name != "hand_ref"+used_side:
                    finger_bones.append(bone.name)

            bpy.ops.armature.select_all(action='DESELECT')

            def get_saved_bone(bone_name):
                for b in scn.arp_fingers_init_transform:
                    if b.name == bone_name:
                        return b

                return None

            # reset fingers transforms if it's the second time the button is pressed
            if len(scn.arp_fingers_init_transform):
                for bone_name in finger_bones:
                    current_bone = get_edit_bone(bone_name)
                    try:
                        b = get_saved_bone(bone_name)
                        if b != None:
                            current_bone.head = b.head
                            current_bone.tail = b.tail
                            current_bone.roll = b.roll
                    except:
                        pass

            # save initial fingers transform in the property collection if it's the first time the button is pressed
            for bone_name in finger_bones:
                current_bone = get_edit_bone(bone_name)
                # is the bone already saved?
                b = get_saved_bone(bone_name)
                # no, save it
                if b == None:
                    item = scn.arp_fingers_init_transform.add()
                    item.name = bone_name
                    item.head = current_bone.head.copy()
                    item.tail = current_bone.tail.copy()
                    item.roll = current_bone.roll


            #    root
            fingers = ["thumb", "index", "middle", "ring", "pinky"]
            if scn.arp_fingers_to_detect == 4:
                fingers.remove("index")

            fingers_root = []#["index1_base_ref"+used_side, "middle1_base_ref"+used_side, "ring1_base_ref"+used_side, "pinky1_base_ref"+used_side]
            for n in fingers:
                if n == "thumb":
                    continue
                fingers_root.append(n+"1_base_ref"+used_side)

            found_fingers_loc = False

            if scn.arp_fingers_to_detect != 0:
                
                # Legacy Metacarpals
                if scn.arp_smart_fingers_engine == 'LEGACY':
                    auto_root = []#["index_root"+ used_side+"_auto", "middle_root"+used_side+"_auto", "ring_root"+used_side+"_auto", "pinky_root"+used_side+"_auto"]
                    for n in fingers:
                        if n == "thumb":
                            continue
                        auto_root.append(n+'_root'+used_side+'_auto')

                    # front view for correct roll from view
                    bpy.ops.view3d.view_axis(type='FRONT')

                    for i in range(0, len(fingers_root)):
                        #if the detection marker exists
                        if get_object(auto_root[i]) != None:

                            found_fingers_loc = True

                            init_selection(fingers_root[i])
                            bpy.context.active_object.data.bones.active = bpy.context.active_object.pose.bones[fingers_root[i]].bone
                            root_ref = get_edit_bone(fingers_root[i])
                            root_ref.head = rig_matrix_world_inv @ get_object(auto_root[i]).location.copy()
                            root_ref.tail = rig_matrix_world_inv @ get_object(fingers[i+1]+'_bot'+used_side+'_auto').location.copy()
                            align_bone_z_axis(root_ref, get_edit_bone('hand_ref'+used_side).z_axis)
                         
                            if scn.arp_smart_sym:
                                mirror_hack()


                for f in range(0, scn.arp_fingers_to_detect):
                    bpy.ops.armature.select_all(action='DESELECT')

                    # if the detection marker exists
                    if (scn.arp_smart_fingers_engine == 'LEGACY' and get_object(fingers[f]+'_bot'+used_side+'_auto') != None) or scn.arp_smart_fingers_engine == 'AI':

                        found_fingers_loc = True

                        # phal1
                        finger1_name = fingers[f]+"1_ref"+used_side
                        init_selection(finger1_name)
                        finger_bot = get_edit_bone(finger1_name)

                        if f != 0:# not thumb
                            phal1_marker_name = fingers[f]+'_bot'+used_side+'_auto'
                            if scn.arp_smart_fingers_engine == 'AI':
                                phal1_marker_name = fingers[f]+'1_loc'
                                if used_side == '.r':
                                    phal1_marker_name += '_sym'
                         
                            phal1_marker = get_object(phal1_marker_name)
                            
                            phal2_name = fingers[f]+"_phal_2"+used_side+"_auto"
                            if scn.arp_smart_fingers_engine == 'AI':
                                phal2_name = fingers[f]+'2_loc'
                                if used_side == '.r':
                                    phal2_name += '_sym'
                                    
                            phal2_marker = get_object(phal2_name)
                                
                            finger_bot.head = rig_matrix_world_inv @ phal1_marker.location
                            finger_bot.tail = rig_matrix_world_inv @ phal2_marker.location

                            # roll                           
                            align_bone_x_axis(get_edit_bone(finger1_name), get_edit_bone('hand_ref'+used_side).x_axis)


                        else:# thumb
                            thumb1_name = fingers[f]+"_root"+used_side+"_auto"
                            if scn.arp_smart_fingers_engine == 'AI':
                                thumb1_name = fingers[f]+'1_loc'
                                if used_side == '.r':
                                    thumb1_name += '_sym'
                            
                            thumb2_name = fingers[f]+"_phal_2"+used_side+"_auto"
                            if scn.arp_smart_fingers_engine == 'AI':
                                thumb2_name = fingers[f]+'2_loc'
                                if used_side == '.r':
                                    thumb2_name += '_sym'
                            
                            thumb1_marker = get_object(thumb1_name)
                            thumb2_marker = get_object(thumb2_name)
                            
                            finger_bot.head = rig_matrix_world_inv @ thumb1_marker.location
                            finger_bot.tail = rig_matrix_world_inv @ thumb2_marker.location
                            bpy.ops.armature.calculate_roll(type='GLOBAL_NEG_Y')

                        if scn.arp_smart_sym:
                            mirror_hack()

                        # phal2
                        phal2_eb_name = fingers[f]+"2_ref"+used_side
                        init_selection(phal2_eb_name)
                        phal2_eb = get_edit_bone(phal2_eb_name)
                        
                        phal_marker_name = fingers[f]+"_phal_1"+used_side+"_auto"
                        if scn.arp_smart_fingers_engine == 'AI':
                                phal_marker_name = fingers[f]+'3_loc'
                                if used_side == '.r':
                                    phal_marker_name += '_sym'
                        
                        phal_marker = get_object(phal_marker_name)
                        phal2_eb.tail = rig_matrix_world_inv @ phal_marker.location

                        # roll
                        if f != 0: #not thumb                            
                            align_bone_x_axis(get_edit_bone(phal2_eb_name), get_edit_bone('hand_ref'+used_side).x_axis)

                        else:# thumb
                            bpy.ops.armature.calculate_roll(type='GLOBAL_NEG_Y')

                        if scn.arp_smart_sym:
                            mirror_hack()


                        #phal3
                        phal3_eb_name = fingers[f]+"3_ref"+used_side
                        init_selection(phal3_eb_name)
                        phal3_eb = get_edit_bone(phal3_eb_name)
                        
                        phal_marker_name = fingers[f]+"_top" + used_side + "_auto"
                        if scn.arp_smart_fingers_engine == 'AI':
                                phal_marker_name = fingers[f]+'4_loc'
                                if used_side == '.r':
                                    phal_marker_name += '_sym'
                        
                        phal_marker = get_object(phal_marker_name)                        
                        phal3_eb.tail = rig_matrix_world_inv @ phal_marker.location

                        # roll
                        if f != 0: #not thumb                           
                            align_bone_x_axis(get_edit_bone(phal3_eb_name), get_edit_bone('hand_ref'+used_side).x_axis)
                        else:
                            bpy.ops.armature.calculate_roll(type='GLOBAL_NEG_Y')

                        if scn.arp_smart_sym:
                            mirror_hack()
                            
                        # AI metacarpals
                        if scn.arp_smart_fingers_engine == 'AI' and f != 0:
                        
                            # front view for correct roll from view
                            bpy.ops.view3d.view_axis(type='FRONT')
                            
                            ref_name = fingers[f]+'1_base_ref'+used_side
                            init_selection(ref_name)
                            hand_ref = get_edit_bone('hand_ref'+used_side)
                            phal1_ref = get_edit_bone(finger1_name)
                            #print('phal1_ref', phal1_ref)
                            bpy.context.active_object.data.bones.active = get_data_bone(ref_name)
                            metacarp_ref = get_edit_bone(ref_name)
                            
                            metacarp_ref.head = hand_ref.head + (phal1_ref.head-hand_ref.head)*0.4
                            # unsqueeze width
                            thumb_ref = get_edit_bone('thumb1_ref'+used_side)
                            dir_fac = 1 if f < 3 else -1
                            fac = 0.8
                            if f == 2 or f == 3:
                                fac = 0.2
                            if f == 4:
                                fac = 0.2
                            metacarp_ref.head += (thumb_ref.head - metacarp_ref.head) * 0.5 * dir_fac * fac
                            
                            align_bone_z_axis(metacarp_ref, hand_ref.z_axis)                            
                         
                            if scn.arp_smart_sym:
                                mirror_hack()
                        

            hand_ref_eb = get_edit_bone('hand_ref'+used_side)
            
            if scn.arp_fingers_enable:                
                # Fingers are enabled, but no fingers were detected
                # move all finger bones close the hand bone
                if (scn.arp_fingers_to_detect == 0 or not found_fingers_loc):
                    # calculate offset vector
                    rig_scale = get_object(rig_name).scale[0]
                    finger_ref_name = 'index'
                    if scn.arp_fingers_to_detect == 4:
                        finger_ref_name = 'middle'
                    if scn.arp_fingers_to_detect == 3:
                        finger_ref_name = 'ring'
                    offset_vec = (hand_ref_eb.tail - get_edit_bone(finger_ref_name+'1_base_ref'+used_side).head)*rig_scale

                    for b in finger_bones:
                        get_edit_bone(b).select = True

                    bpy.ops.object.mode_set(mode='POSE')
                    bpy.ops.object.mode_set(mode='EDIT')
                    bpy.ops.transform.translate(value=(offset_vec), constraint_axis=(False, False, False), orient_type='GLOBAL', mirror=True)

                    bpy.ops.armature.select_all(action='DESELECT')
            else:
                # Fingers are disabled
                # the hand bone tail should match the hand_tip marker loc
                hand_tip_name = "hand_tip_loc" if used_side == '.l' else "hand_tip_loc_sym"
                hand_tip_marker = get_object(hand_tip_name)
                if hand_tip_marker:
                    if scn.arp_smart_depth and hand_tip_marker:# only evaluates the hand_tip marker if depth is enabled, wrong results otherwise
                        hand_ref_eb.tail = rig_matrix_world_inv @ hand_tip_marker.location                 


    # Facial
    if get_object("arp_facial_setup"):
        print("\n    matching smart facial...")
        
        # disable x-axis mirror edit
        bpy.context.active_object.data.use_mirror_x = False
        facial_markers = ard.facial_markers

        # enable ears and facial
        if scn.arp_smart_ears:
            suffix, found_base = auto_rig.get_next_dupli_id(".l", "ears")
            if not found_base:
                auto_rig.set_ears(2, side_arg=".l")
        
        # set facial
        head_ref = get_edit_bone("head_ref.x")
        head_ref.select = True
        
        auto_rig.set_facial(enable=True, eyebrow_l_enabled=scn.arp_smart_eyebrows, eyebrow_r_enabled=scn.arp_smart_eyebrows,
            noses_enabled=scn.arp_smart_nose, cheeks_enabled=scn.arp_smart_cheeks, eye_l_enabled=scn.arp_smart_eyes, eye_r_enabled=scn.arp_smart_eyes,
            mouth_enabled=scn.arp_smart_mouth, teeth_enabled=scn.arp_smart_teeth, tongue_enabled=scn.arp_smart_tongue, chins_enabled=scn.arp_smart_chin)

        eyelids_pos_list = []
        eyelid_pos = None
        
        # match
        _eyeball_loc = None
        
        for bone in facial_markers:
            _side = bone[-2:]
            e_bone = get_edit_bone(bone[:-2]+"_ref"+_side)
            
            cur_eyeball_loc = None
            
            if scn.arp_smart_eyes:
                cur_eyeball_loc = eyeball_loc
                if _side == ".r" and scn.arp_smart_sym == False and scn.arp_eyeball_type == "SEPARATE":# right eyeball loc
                    cur_eyeball_loc = eyeball_loc_right

            if e_bone:
                e_bone_vec = e_bone.tail - e_bone.head
                v_index = facial_markers[bone]
                vert_loc = arp_facial_setup.matrix_world @ arp_facial_setup.data.vertices[v_index].co

                if 'eyelid' in bone and scn.arp_smart_eyes:
                    _eyeball_loc = cur_eyeball_loc.copy()
                    _eyeball_loc[0] = abs(cur_eyeball_loc[0]) if _side == ".l" else -abs(cur_eyeball_loc[0])
                    e_bone.head = rig_matrix_world_inv @ _eyeball_loc
                    e_bone.tail = rig_matrix_world_inv @ vert_loc
                    align_bone_x_axis(e_bone, Vector((-1,0,0)))
                    eyelids_pos_list.append(e_bone.head.copy())
                
                elif 'ear_01' in bone and scn.arp_smart_ears:
                    vert_ear2 = arp_facial_setup.matrix_world @ arp_facial_setup.data.vertices[facial_markers['ear_02'+_side]].co
                    mid = (vert_ear2 + vert_loc)*0.5
                    e_bone.head = rig_matrix_world_inv @ vert_loc
                    e_bone.tail = rig_matrix_world_inv @ mid

                elif 'ear_02' in bone and scn.arp_smart_ears:
                    vert_ear1 = arp_facial_setup.matrix_world @ arp_facial_setup.data.vertices[facial_markers['ear_01'+_side]].co
                    mid = (vert_ear1 + vert_loc)*0.5
                    e_bone.head = rig_matrix_world_inv @ mid
                    e_bone.tail = rig_matrix_world_inv @ vert_loc                    
             
                else:
                    e_bone.head = rig_matrix_world_inv @ vert_loc
                    e_bone.tail = e_bone.head + e_bone_vec

                if 'chin_0' in bone or 'cheek_inflate' in bone:#push back chin
                    push_vec = (e_bone.head - e_bone.tail)
                    e_bone.head += push_vec*0.5
                    e_bone.tail += push_vec*0.5
        
        sum = None
        mid_pos = None
        
        for pos in eyelids_pos_list:
            if sum == None:
                sum = pos
            else:
                sum += pos
        if sum:
            mid_pos = sum/len(eyelids_pos_list)
        else:
            mid_pos = (head_ref.head + head_ref.tail)*0.5
        
        for _side in sides:

            #eyebrow master        
            if scn.arp_smart_eyebrows:            
                eyebrow_full = get_edit_bone("eyebrow_full_ref"+_side)
                if eyebrow_full:
                    eybrow_02 = get_edit_bone("eyebrow_02_ref"+_side)
                    eyebrow_full.head = eybrow_02.tail + (eybrow_02.tail - eybrow_02.head) * 2
                    eyebrow_full.tail = eyebrow_full.head + (eybrow_02.tail - eybrow_02.head)

            #main eyelids
            if scn.arp_smart_eyes:
                cur_eyeball_loc = eyeball_loc

                if _side == ".r" and scn.arp_smart_sym == False and scn.arp_eyeball_type == "SEPARATE":# right eyeball loc
                    cur_eyeball_loc = eyeball_loc_right
                
                if _side == ".r":# and not scn.arp_smart_sym == False and not scn.arp_eyeball_type == "SEPARATE":
                    _eyeball_loc[0] = -abs(cur_eyeball_loc[0])
                else:
                    _eyeball_loc[0] = abs(cur_eyeball_loc[0])

                eyeball_loc_final = rig_matrix_world_inv @ _eyeball_loc

                #  top
                eyelid_top = get_edit_bone('eyelid_top_ref'+_side)
                eyelid_top.head = eyeball_loc_final
                eyelid_top.tail = get_edit_bone('eyelid_top_02_ref'+_side).tail
                eyelid_top.tail[0] = eyelid_top.head[0]
                eyelid_top.roll = math.radians(180)

                #bottom
                eyelid_bot = get_edit_bone("eyelid_bot_ref"+_side)
                eyelid_bot.head = eyeball_loc_final
                eyelid_bot.tail = get_edit_bone("eyelid_bot_02_ref"+_side).tail
                eyelid_bot.tail[0] = eyelid_bot.head[0]
                eyelid_bot.roll = math.radians(180)

                #eye offset
                eye_offset = get_edit_bone("eye_offset_ref"+_side)
                eye_offset.head = eyeball_loc_final
                eye_offset.tail = eyelid_bot.tail
                eye_offset.tail[2] = eye_offset.head[2]
                align_bone_x_axis(eye_offset, Vector((-1,0,0)))
            
            if scn.arp_smart_mouth:
                #lips corner mini
                lips_corner = get_edit_bone("lips_smile_ref"+_side)
                lips_cm = get_edit_bone("lips_corner_mini_ref" + _side)
                lips_cm.head = lips_corner.head
                lips_cm.tail = lips_corner.head + (lips_corner.tail - lips_corner.head)*0.5
                
        # end for _side in sides

        #nose 01 tweak
        nose_01 = get_edit_bone("nose_01_ref.x")
        if nose_01:
            nose_03 = get_edit_bone("nose_03_ref.x")
            
            if scn.arp_smart_eyes:
                nose_01.head[1] = ((rig_matrix_world_inv @ _eyeball_loc)[1] + nose_01.tail[1])*0.5
            else:
                nose_01.head[1] = nose_03.head[1]
                
            nose_01.tail = nose_01.head + (nose_01.tail - nose_01.head)*0.3

            #nose 02
            nose_02 = get_edit_bone("nose_02_ref.x")
            nose_02.head = nose_01.tail
            nose_02.tail = nose_02.head + (nose_01.tail - nose_01.head)

            #nose 03 tweak
            transf_vec = nose_03.head - nose_03.tail
            nose_03.head += transf_vec*0.5
            nose_03.tail += transf_vec*0.5

        if scn.arp_smart_mouth:
            #lips roll
            lips_roll_t = get_edit_bone("lips_roll_top_ref.x")
            lips_top = get_edit_bone("lips_top_ref.x")
            initial_vec = lips_roll_t.tail - lips_roll_t.head
            if nose_01:        
                mid_pos = (nose_02.tail + lips_top.head) * 0.5
            lips_roll_t.head = mid_pos
            lips_roll_t.tail = initial_vec + lips_roll_t.head

            lips_roll_b = get_edit_bone("lips_roll_bot_ref.x")
            lips_bot = get_edit_bone("lips_bot_ref.x")
            initial_vec = lips_roll_b.tail - lips_roll_b.head
            
            pos = rig.matrix_world.inverted() @ vectorize3(rig.data["arp_chin_pos_vec"])
            chin_01_ref = get_edit_bone("chin_01_ref.x")
            if chin_01_ref:
                pos = chin_01_ref.head
            mid_vec = (pos + lips_bot.head) * 0.5
            lips_roll_b.head = mid_vec
            lips_roll_b.head[1] = lips_roll_t.head[1]
            lips_roll_b.tail = initial_vec + lips_roll_b.head

            #jaw
            jaw_bone = get_edit_bone("jaw_ref.x")
            head_ref = get_edit_bone("head_ref.x")
            chin_02_ref = get_edit_bone("chin_02_ref.x")
            chin_pos = rig.matrix_world.inverted() @ vectorize3(rig.data["arp_chin_pos_vec"])
            
            if chin_02_ref:
                chin_pos = chin_02_ref.head.copy()
            
            jaw_bone.head = head_ref.head + (head_ref.tail - head_ref.head)*0.2 + (chin_pos - head_ref.head)*0.2
            jaw_bone.tail = chin_pos
 

            # Tongue
            if nose_01:
                nose_lips_point = (lips_top.head + nose_01.tail) * 0.5
            else:
                nose_lips_point = (lips_top.head + mid_pos) * 0.5
                
            if scn.arp_smart_teeth:
                transf_vec = nose_lips_point - (get_edit_bone("teeth_top_ref.x").tail)
            else:
                transf_vec = nose_lips_point - Vector((jaw_bone.tail[0], jaw_bone.tail[1], jaw_bone.head[2]))
            transf_vec += (jaw_bone.head - lips_top.head) * 0.2
                
            tongue_object = get_object(scn.arp_tongue_name)
            
            tongue_raycasted = False
            
            if scn.arp_smart_tongue:
                tongue_names = ["tong_01_ref.x", "tong_02_ref.x", "tong_03_ref.x"]
                
                if tongue_object:# get exact tongue positions from object raycast
                    unhide_object(tongue_object)
                    tongue_object.hide_select = False
                    bounds = get_object_boundaries(tongue_object)
                    depsgraph = bpy.context.evaluated_depsgraph_get()
                    obj_eval = depsgraph.objects.get(tongue_object.name, None)
                    y_fac = [0.1, 0.5, 0.85]
                    
                    for idx in range(0, 3):
                        print('    Raycast tongue #'+str(idx)+'...')                
                        y = bounds['back'] + (bounds['front']-bounds['back'])*y_fac[idx]
                        x = (bounds['left']+bounds['right'])*0.5
                        z = bounds['top'] + (bounds['top']-bounds['bottom'])*0.5
                        ray_origin = tongue_object.matrix_world.inverted() @ Vector((x, y, z))
                        ray_dir = tongue_object.matrix_world.inverted() @ vectorize3([0.0, 0.0, -10.0])
                        ray_inc = ray_dir.normalized() * 0.0001
                        result, loc, normal, index = obj_eval.ray_cast(ray_origin, ray_dir)

                        hit_front = None
                        
                        if result:        
                            hit_front = loc.copy()
                            have_hit = True
                            last_hit = loc                
                            while have_hit:#iterate if multiples faces layers
                                have_hit = False
                                result, loc, normal, index = obj_eval.ray_cast(last_hit+ray_inc, ray_dir)
                                if result:
                                    have_hit = True
                                    last_hit = loc
                            hit_back = last_hit
                        else:
                            print('    Tongue raycast'+str(idx)+' failed!')

                        if hit_front:
                            tongue_raycasted = True
                            hit_center = (hit_front + hit_back) * 0.5
                            tongue_xx_loc = obj_eval.matrix_world @ hit_center# convert to world space
                            tongue_xx_loc = rig_matrix_world_inv @ tongue_xx_loc# convert to armature space
                            tongue_xx = get_edit_bone(tongue_names[idx])
                            move_vec = (tongue_xx_loc - tongue_xx.head)
                            tongue_xx.head += move_vec
                            if idx == 2:
                                tongue_xx.tail += move_vec
                    
                if tongue_raycasted == False:# no tongue_object, or raycast failed, then average tongue position
                    for name in tongue_names:
                        if 'tong_03' in name:
                            get_edit_bone(name).head += transf_vec
                            get_edit_bone(name).tail += transf_vec
                        else:
                            get_edit_bone(name).head += transf_vec
                            
            
            # Teeth
            if scn.arp_smart_teeth:
                teeth_names = ["teeth_top_ref.l", "teeth_top_ref.x", "teeth_top_ref.r", "teeth_bot_ref.l", "teeth_bot_ref.x", "teeth_bot_ref.r"]   
                
                teeth_object = get_object(scn.arp_teeth_name)
                if teeth_object:# get exact teeth positions from object
                    unhide_object(teeth_object)
                    teeth_object.hide_select = False       
                    bounds = get_object_boundaries(teeth_object)
                   
                    # teeth_top_ref.x
                    x = (bounds['left']+bounds['right']) * 0.5
                    y = bounds['front'] + (bounds['back']-bounds['front'])*0.2
                    z = bounds['top'] + (bounds['bottom']-bounds['top'])*0.2
                    
                    teeth_top_mid_loc = rig_matrix_world_inv @ Vector((x, y, z))
                    teeth_top_mid = get_edit_bone(teeth_names[1])
                    move_vec = (teeth_top_mid_loc - teeth_top_mid.head)
                    teeth_top_mid.head += move_vec
                    teeth_top_mid.tail += move_vec
                    
                    # teeth_top_ref.l
                    x = bounds['left'] + (bounds['right']-bounds['left']) * 0.1
                    y = bounds['back'] + (bounds['front']-bounds['back'])*0.2
                    z = bounds['top'] + (bounds['bottom']-bounds['top'])*0.2
                    
                    teeth_top_lft_loc = rig_matrix_world_inv @ Vector((x, y, z))
                    teeth_top_left = get_edit_bone(teeth_names[0])
                    move_vec = (teeth_top_lft_loc - teeth_top_left.head)
                    teeth_top_left.head += move_vec
                    teeth_top_left.tail += move_vec
                    
                    # teeth_top_ref.r
                    x = bounds['right'] + (bounds['left']-bounds['right']) * 0.1
                    y = bounds['back'] + (bounds['front']-bounds['back'])*0.2
                    z = bounds['top'] + (bounds['bottom']-bounds['top'])*0.2
                    
                    teeth_top_right_loc = rig_matrix_world_inv @ Vector((x, y, z))
                    teeth_top_right = get_edit_bone(teeth_names[2])
                    move_vec = (teeth_top_right_loc - teeth_top_right.head)
                    teeth_top_right.head += move_vec
                    teeth_top_right.tail += move_vec
                    
                    lower_teeth = get_object(scn.arp_teeth_lower_name)            
                    if lower_teeth:
                        unhide_object(lower_teeth)
                        lower_teeth.hide_select = False
                        bounds = get_object_boundaries(lower_teeth)
                        
                    # teeth_bot_ref.x
                    x = (bounds['left']+bounds['right']) * 0.5
                    y = bounds['front'] + (bounds['back']-bounds['front'])*0.2
                    z = bounds['bottom'] + (bounds['top']-bounds['bottom'])*0.2
                    
                    teeth_bot_mid_loc = rig_matrix_world_inv @ Vector((x, y, z))
                    teeth_bot_mid = get_edit_bone(teeth_names[4])
                    move_vec = (teeth_bot_mid_loc - teeth_bot_mid.head)
                    teeth_bot_mid.head += move_vec
                    teeth_bot_mid.tail += move_vec
                    
                    # teeth_bot_ref.l
                    x = bounds['left'] + (bounds['right']-bounds['left']) * 0.1
                    y = bounds['back'] + (bounds['front']-bounds['back'])*0.2
                    z = bounds['bottom'] + (bounds['top']-bounds['bottom'])*0.2
                    
                    teeth_bot_lft_loc = rig_matrix_world_inv @ Vector((x, y, z))
                    teeth_bot_left = get_edit_bone(teeth_names[3])
                    move_vec = (teeth_bot_lft_loc - teeth_bot_left.head)
                    teeth_bot_left.head += move_vec
                    teeth_bot_left.tail += move_vec
                    
                    # teeth_bot_ref.r
                    x = bounds['right'] + (bounds['left']-bounds['right']) * 0.1
                    y = bounds['back'] + (bounds['front']-bounds['back'])*0.2
                    z = bounds['bottom'] + (bounds['top']-bounds['bottom'])*0.2
                    
                    teeth_bot_right_loc = rig_matrix_world_inv @ Vector((x, y, z))
                    teeth_bot_right = get_edit_bone(teeth_names[5])
                    move_vec = (teeth_bot_right_loc - teeth_bot_right.head)
                    teeth_bot_right.head += move_vec
                    teeth_bot_right.tail += move_vec
                    
                    
                else:# average teeth position
                    for name in teeth_names:   
                        teeth_b = get_edit_bone(name)
                        teeth_b.head += transf_vec
                        teeth_b.tail += transf_vec

    else:# no arp_facial_setup
        auto_rig.set_facial(enable=False)
        

    # display reference layer only
    enable_layer_exclusive('Reference')
   
    print("\n    matching end.")
    bpy.ops.armature.select_all(action='DESELECT')


def _set_skeleton(self):    
 
    rig = get_object(bpy.context.active_object.name)
    scn = bpy.context.scene

    # Spine
    print("Smart set spine...")
    # store current detected spine positions
    neck_ref = get_edit_bone('neck_ref.x')
    root_ref = get_edit_bone('root_ref.x')
    spine_01_ref = get_edit_bone('spine_01_ref.x')
    spine_02_ref = get_edit_bone('spine_02_ref.x')
    
    spine_pos_1 = spine_01_ref.head.copy()
    spine_pos_2 = spine_02_ref.head.copy()
    spine_points = [root_ref.head.copy(), spine_01_ref.head.copy(), spine_02_ref.head.copy(), neck_ref.head.copy()]        
                
    # set spine count
    if scn.arp_smart_spine_count != 3 or scn.arp_smart_spine_shape == 'STRAIGHT':
        auto_rig.set_spine(count=scn.arp_smart_spine_count, grid_align=True, bottom=False)
        
    # need to re-get references, set_spine() is switching mode
    neck_ref = get_edit_bone('neck_ref.x')
    root_ref = get_edit_bone('root_ref.x')
        
    if scn.arp_smart_spine_shape == 'MODEL_FIT':
        if scn.arp_smart_spine_count != 3:# only need to adjust the position if different from 3. By default (=3), already fit
            # generate nurbs
            resol = scn.arp_smart_spine_count * 500
            spine_nurbs = generate_nurbs_curve(spine_points, num_points=resol, degree=2)
            curve_length = get_curve_length(spine_nurbs)
            spine_points_def = resample_curve(spine_nurbs, length=curve_length, amount=scn.arp_smart_spine_count, symmetrical=False)
            
            # align spines
            for i in range(1, scn.arp_smart_spine_count):
                str_i = '%02d' % i
                spine_name = 'spine_'+str_i+'_ref.x'
                spine_ref = get_edit_bone(spine_name)
                spine_ref.head = spine_points_def[i]
            
    elif scn.arp_smart_spine_shape == 'ARCHED': 
        spine_vec = neck_ref.head - root_ref.head
        spine_1_pos = root_ref.head + (spine_vec * 0.33)
        spine_2_pos = root_ref.head + (spine_vec * 0.67)
        spine_1_forward = spine_1_pos + (spine_vec.magnitude * 0.1) * Vector((0,-1,0))
        spine_2_forward = spine_2_pos + (spine_vec.magnitude * 0.11) * Vector((0,-1,0))
        spine_points = [root_ref.head.copy(), spine_1_forward, spine_2_forward, neck_ref.head.copy()] 
      
        # generate nurbs
        resol = scn.arp_smart_spine_count * 500
        spine_nurbs = generate_nurbs_curve(spine_points, num_points=resol, degree=2)
        
        '''
        # debug, draw NURBS
        for i, p in enumerate(spine_nurbs):
            b = create_edit_bone('b'+str(i))
            b.head = p
            b.tail = p + Vector((0,0,0.01))
        '''    
        
        curve_length = get_curve_length(spine_nurbs)
        spine_points_def = resample_curve(spine_nurbs, length=curve_length, amount=scn.arp_smart_spine_count, symmetrical=False)
        
        # align spines
        for i in range(1, scn.arp_smart_spine_count):
            str_i = '%02d' % i
            spine_name = 'spine_'+str_i+'_ref.x'
            spine_ref = get_edit_bone(spine_name)
            spine_ref.head = spine_points_def[i]
        

    root_ref = get_edit_bone('root_ref.x')
    spine_01_ref = get_edit_bone('spine_01_ref.x')
    
    if scn.arp_smart_root_vertical:
        if spine_01_ref and not scn.arp_smart_spine_shape == 'ARCHED':            
            spine_01_ref.use_connect = False
        
        root_ref.tail[1] = root_ref.head[1]
        root_ref.tail[0] = root_ref.head[0]
        
        
    # reproportion spine bones in 'Arched' mode to better fit the UE5 spine proportions
    if scn.arp_smart_spine_shape == 'ARCHED' and scn.arp_smart_spine_count == 6: 
        spine_02_ref = get_edit_bone('spine_02_ref.x')
        spine_03_ref = get_edit_bone('spine_03_ref.x')
        spine_04_ref = get_edit_bone('spine_04_ref.x')
        spine_05_ref = get_edit_bone('spine_05_ref.x')
        
        root_ref_length = (root_ref.tail-root_ref.head).magnitude
        
        root_ref.tail = root_ref.head + (root_ref.tail-root_ref.head)*0.4
        spine_01_ref.tail = spine_01_ref.head + (spine_01_ref.tail-spine_01_ref.head)*0.4
        spine_02_ref.tail = spine_02_ref.head + (spine_02_ref.tail-spine_02_ref.head)*0.45
        spine_03_ref.tail = spine_03_ref.head + (spine_03_ref.tail-spine_03_ref.head)*0.5
        spine_04_ref.tail = spine_04_ref.head + (spine_04_ref.tail-spine_04_ref.head)*0.9
        
        spines_list = [root_ref, spine_01_ref, spine_02_ref, spine_03_ref, spine_04_ref, spine_05_ref]
        
        # disconnect and restore lengths
        for i, spine_ref in enumerate(spines_list):
            if i != len(spines_list)-1:
                next_spine = spines_list[i+1]
                next_spine.use_connect = False
            spine_ref.tail = spine_ref.head + (spine_ref.tail- spine_ref.head).normalized() * root_ref_length*1.5
        
        
    # Neck
    auto_rig.set_neck(scn.arp_smart_neck_count, twist=True, bendy_segments=1)
    
    # Twists
    auto_rig.set_leg_twist(scn.arp_smart_twist_count, '.l', bbones_ease_out=None)
    auto_rig.set_leg_twist(scn.arp_smart_twist_count, '.r', bbones_ease_out=None)
    auto_rig.set_arm_twist(scn.arp_smart_twist_count, '.l', bbones_ease_out=None)
    auto_rig.set_arm_twist(scn.arp_smart_twist_count, '.r', bbones_ease_out=None)
    
    #  Shoulders
    shoulder_ref_name = ard.arm_ref_dict['shoulder']
    
    if scn.arp_smart_shoulders_align == 'STRAIGHT':# aligned on Y        
        for side in ['.l', '.r']:
            shoulder = get_edit_bone(shoulder_ref_name+side)
            shoulder.head[1] = shoulder.tail[1]
            
    elif scn.arp_smart_shoulders_align == 'TILTED':#UE5 Manny shoulders are down
        
        shoulder_l = get_edit_bone(shoulder_ref_name+'.l')
        shoulder_r = get_edit_bone(shoulder_ref_name+'.r')
        shoulder_mid = (shoulder_l.tail + shoulder_r.tail) * 0.5
        
        for side in ['.l', '.r']:
            shoulder = get_edit_bone(shoulder_ref_name+side)
            shoulder.head = shoulder.tail + (shoulder_mid-shoulder.tail) * 0.9# bring them closer to the center on X
            shoulder.head[1] = shoulder.tail[1]# align Y
            shoulder.head[2] = shoulder.head[2] + (shoulder.tail-shoulder.head).magnitude * 0.1# tilt down by moving the head up
            
            align_bone_x_axis(shoulder, Vector((0,-1,0)))
            if side == '.r':
                shoulder.roll += math.radians(180)
                
        # move the shoulder custom shape on the sides, too close to the center otherwise
        bpy.ops.object.mode_set(mode='POSE')
        
        for side in ['.l', '.r']:
            c_shoulder_name = 'c_shoulder'+side
            c_shoulder = get_pose_bone(c_shoulder_name)
            cs = c_shoulder.custom_shape
            if cs:
                for vert in cs.data.vertices:
                    vert.co[1] += 0.4
            
        
        bpy.ops.object.mode_set(mode='EDIT')
                
            
def create_arp_markers():
    bpy.ops.object.empty_add(type='PLAIN_AXES', radius = 0.01, location=(0.0, 0.0, 0.0), rotation=(0.0, 0.0, 0.0))
    am_obj = get_object(bpy.context.active_object.name)
    am_obj.name = "arp_markers"
    am_obj.hide_select = True
    
    # Assign to main scene collection
    try:
        bpy.context.scene.collection.objects.link(am_obj)
    except:
        pass
    # remove previous uiser active collections if any
    for i in am_obj.users_collection:
        if i != bpy.context.scene.collection:
            i.objects.unlink(am_obj)

        
def _add_marker(_name, enable_mirror):
    body = get_object(bpy.context.scene.arp_body_name)
    body_height = body.dimensions[2]
    scaled_radius = body_height/200
    scn = bpy.context.scene
    
    def is_finger_marker(_name):
        if 'thumb' in _name or 'index' in _name or 'middle' in _name or 'ring' in _name or 'pinky' in _name:
            return True
        return False
        
    
    def assign_marker_collec(obj_marker):
        # Assign to main scene collection
        try:
            bpy.context.scene.collection.objects.link(obj_marker)
        except:
            pass
        # remove previous user active collections if any
        for i in obj_marker.users_collection:
            if i != bpy.context.scene.collection:
                i.objects.unlink(obj_marker)
                
                
    def create_empty_img(marker_object):
        empty_img = bpy.data.objects.new(name=marker_object.name+'_img', object_data=None)
        empty_img.location = marker_object.location.copy()
        empty_img.parent = marker_object
        empty_img.rotation_euler[0] = math.radians(90)
        empty_img.hide_select = True        
        empty_img.empty_display_type = 'IMAGE'
        empty_img.use_empty_image_alpha = True
        
        # get image icon
        img_id_name = 'arp_smart_circle'
        img = bpy.data.images.get(img_id_name)
        if img == None:
            dir = os.path.dirname(os.path.abspath(__file__))
            addon_dir = os.path.dirname(dir)
            fp = addon_dir + '/icons/circle.png'
            img = bpy.data.images.load(fp)
            img.name = img_id_name
        empty_img.data = img
        empty_img.empty_image_depth = 'FRONT'

        try:
            bpy.context.scene.collection.objects.link(empty_img)
        except:
            pass

        empty_img.empty_display_size = body_height/20
        
        if 'thumb' in _name or 'index' in _name or 'middle' in _name or 'ring' in _name or 'pinky' in _name:
            empty_img.empty_display_size *= 0.35
            
    
    #apply mesh rotation
    set_active_object(body.name)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    try:
        bpy.ops.object.mode_set(mode='OBJECT')
    except: pass

    # create an empty parent for the markers
    if get_object("arp_markers") == None:
        create_arp_markers()  
     
    # create the marker if not exists already
    if get_object(_name+"_loc"): #it already exists
        bpy.ops.object.select_all(action='DESELECT')
        get_object(_name+"_loc").select_set(state=1)
        set_active_object(_name+"_loc")
    else:
        bpy.ops.object.select_all(action='DESELECT')
        #create it
        bpy.ops.object.empty_add(type='PLAIN_AXES', radius=scaled_radius, location=(0.0, 0.0, 0.0), rotation=(0.0, 0.0, 0.0))
        
        obj_marker = get_object(bpy.context.active_object.name)
        obj_marker.empty_display_type = 'CIRCLE'
        obj_marker.empty_display_size = scaled_radius
        # rename it
        obj_marker.name = _name+"_loc"
        # parent it
        obj_marker.parent = get_object("arp_markers")
        #enable xray
        obj_marker.show_in_front = True
        
        assign_marker_collec(obj_marker)            
        
            
        if _name in ["shoulder", "hand", "foot", "thigh", "knee", "hand_tip", "elbow"] or is_finger_marker(_name):
            # add limit constraint
            cns = bpy.context.active_object.constraints.new('LIMIT_LOCATION')
            cns.use_min_x = True
            cns.use_transform_limit = True

            # create mirror markers with constraint
            bpy.ops.object.empty_add(type='PLAIN_AXES', radius=scaled_radius, location=(0,0,0), rotation=(0, 0, 0))
            marker_sym = get_object(bpy.context.active_object.name)
            marker_sym.empty_display_type = 'CIRCLE'
            marker_sym.empty_display_size = scaled_radius

            # rename it
            marker_sym.name = _name+"_loc_sym"

            # parent it
            marker_sym.parent = get_object("arp_markers")
            #print("parent", marker_sym.name, "to arp_markers")

            #enable xray
            marker_sym.show_in_front = True
            
            assign_marker_collec(marker_sym)
            
            #add mirror constraint
            cns = marker_sym.constraints.new('COPY_LOCATION')
            cns.target = get_object(_name+"_loc")
            cns.invert_x = True

            if enable_mirror == False:
                cns.influence = 0.0

            #add limit constraint
            cns = marker_sym.constraints.new('LIMIT_LOCATION')
            cns.use_max_x = True
            cns.use_transform_limit = True
            
            if scn.arp_disable_smart_fx:
                create_empty_img(marker_sym)
                
            #select back the main empty
            set_active_object(_name+"_loc")
            

    # markers specific options
    if bpy.context.scene.arp_smart_sym:
        if _name == "neck" or _name == "root" or _name == "chin" or _name == 'head_tip':
            bpy.context.active_object.lock_location[0] = True
         
    # use empty images if real FX drawing is disabled (Mac issues)
    if scn.arp_disable_smart_fx:
        create_empty_img(obj_marker)
    
        


def _auto_detect(self):
    print("\nAuto-Detecting... \n")
    
    scn = bpy.context.scene
    
    set_selection_filters(['EMPTY', 'MESH', 'ARMATURE'], True)
    show_extras(True)
    
    # get character mesh name
    body = get_object(scn.arp_body_name)

    # apply transforms
    bpy.ops.object.select_all(action='DESELECT')
    set_active_object(body.name)
    
    #   delta values must be reset as well, issues with raycast otherwise
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    body.location += body.delta_location.copy()
    
    for i, j in enumerate(body.rotation_euler):
        body.rotation_euler[i] += body.delta_rotation_euler[i]
    body.scale += (body.delta_scale.copy() - Vector((1,1,1)))
    body.delta_location = body.delta_rotation_euler =[0,0,0]
    body.delta_scale = [1,1,1]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    # remove shape keys if any
    try:
        bpy.ops.object.shape_key_remove(all=True)
    except:
        pass

    # get its dimension
    body_width = body.dimensions[0]
    body_height = body.dimensions[2]
    body_depth = body.dimensions[1]

    hand_offset = [0,0,0]

    # create an empty group for the auto detected empties
    #   delete existing if any
    for obj in bpy.data.objects:
        if obj.type == 'EMPTY':
            if 'auto_detect_loc' in obj.name:
                if len(obj.children) == 0:
                    bpy.data.objects.remove(obj, do_unlink=True)


    _delete_detected()

    #   create it
    bpy.ops.object.empty_add(type='PLAIN_AXES', radius = 0.01, location=(0,0,0), rotation=(0, 0, 0))
    bpy.context.active_object.name = "auto_detect_loc"
    bpy.context.active_object.parent = get_object("arp_temp_detection")
    
    bpy.ops.object.select_all(action='DESELECT')

    #  save current pivot mode
    pivot_mod = scn.tool_settings.transform_pivot_point
    
    if scn.arp_smart_type == 'BODY':
        # Arms
        #   get the loc guides
        hand_loc_l = get_object("hand_loc")
        hand_loc_r = get_object("hand_loc_sym")
      
        hand_empty_loc_l = None
        hand_empty_loc_r = None

        hand_markers = [hand_loc_l]

        if not scn.arp_smart_sym:
            hand_markers.append(hand_loc_r)

        # iterate on left and right sides
        for side_idx, hand_marker in enumerate(hand_markers):

            if side_idx == 0:
                print('\n[Left arm detection...]')
            if side_idx == 1:
                print('\n[Right arm detection...]')

            set_active_object(body.name)
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            bpy.ops.object.mode_set(mode='EDIT')
            # check for hidden vertices, can't be accessed if hidden
            bpy.ops.mesh.reveal()
            bpy.ops.mesh.select_all(action='DESELECT')
            # get the mesh (in edit mode only)
            mesh = bmesh.from_edit_mesh(bpy.context.active_object.data)

            # HAND DETECTION ----------

            if scn.arp_debug_mode:
                print("    Find hands boundaries...\n")

            print("    Find wrist...\n")

            # find wrist center and bounds by raycast
            wrist_bound_back = None
            my_tree = BVHTree.FromBMesh(mesh)

            ray_origin = hand_marker.location + vectorize3([0, -body_depth*5, 0])
            ray_dir = vectorize3([0, body_depth*50, 0])
            
            hit, normal, index, distance = my_tree.ray_cast(ray_origin, ray_dir, ray_dir.magnitude)

            if hit == None or distance < 0.001:
                print('    Could not find wrist front, marker out of mesh')
            else:
                wrist_bound_front = hit[1]
                have_hit = True
                last_hit = hit
                #iterate if multiples faces layers
                while have_hit:
                    have_hit = False
                    hit, normal, index, distance = my_tree.ray_cast(last_hit+vectorize3([0,0.001,0]), ray_dir, ray_dir.magnitude)
                    if hit != None:
                        have_hit = True
                        last_hit = hit

                wrist_bound_back = last_hit[1]

            
            if wrist_bound_back == None:      
                self.error_message = 'Could not find the wrist, marker out of mesh?'
                self.error_during_auto_detect = True
                return

            hand_loc_x = hand_marker.location[0]
            hand_loc_y = hand_marker.location[1]            
            if not scn.arp_smart_depth:
                hand_loc_y = wrist_bound_back + ((wrist_bound_front - wrist_bound_back)*0.5)
                
            hand_loc_z = hand_marker.location[2]

            # Sides naming handling
            suff = ""
            side = ".l"
            if side_idx == 0:
                hand_empty_loc_l = [hand_loc_x, hand_loc_y, hand_loc_z]
            if side_idx == 1:
                hand_empty_loc_r = [hand_loc_x, hand_loc_y, hand_loc_z]
                suff = "_sym"
                side = ".r"


            # ARMS -------

            print("    Find arms...\n")

            shoulder_loc = get_object("shoulder_loc"+suff)
            shoulder_front = None
            shoulder_back = None

            if scn.arp_debug_mode:
                print("    Find shoulders...\n")

            ray_origin = shoulder_loc.location + vectorize3([0, -body_depth*2, 0])
            ray_dir = vectorize3([0, body_depth*4, 0])

            hit, normal, index, distance = my_tree.ray_cast(ray_origin, ray_dir, ray_dir.magnitude)

            if hit == None or distance < 0.001:
                print('    Could not find shoulder, marker out of mesh?')
            else:
                shoulder_front = hit[1]
                have_hit = True
                last_hit = hit
                #iterate if multiples faces layers
                while have_hit:
                    have_hit = False
                    hit, normal, index, distance = my_tree.ray_cast(last_hit+vectorize3([0,0.001,0]), ray_dir, ray_dir.magnitude)
                    if hit != None:
                        have_hit = True
                        last_hit = hit

                shoulder_back = last_hit[1]

            shoulder_depth = 0.0
            
            if scn.arp_smart_depth:
                shoulder_depth = shoulder_loc.location[1]
            else:
                shoulder_depth = shoulder_back + (shoulder_front-shoulder_back)*0.4                
                
            shoulder_empty_loc = [shoulder_loc.location[0], shoulder_depth, shoulder_loc.location[2]]

            # Shoulder_base
            # Y position: best to bring it forward for best compatibility with humanoid rigs (UE) (Model Fit only)
            base_depth = 0.0
            if scn.arp_smart_depth:
                base_depth = shoulder_empty_loc[1] + (shoulder_front-shoulder_empty_loc[1])*0.5
            else:
                
                base_depth = shoulder_back + (shoulder_front-shoulder_back)*0.8                
                
            shoulder_base_loc = [shoulder_empty_loc[0]/4, base_depth, shoulder_empty_loc[2]]
            
            
            # Elbow
            _hand_empty_loc = hand_empty_loc_l if side_idx == 0 else hand_empty_loc_r   
            
            #   auto elbow loc
            elbow_empty_loc = Vector(( (shoulder_empty_loc[0] + _hand_empty_loc[0])/2, 0, (shoulder_empty_loc[2] + _hand_empty_loc[2])/2 ))
            
            #   from marker
            elbow_loc_obj = get_object('elbow_loc') if side_idx == 0 else get_object('elbow_loc_sym')
            if elbow_loc_obj:
                elbow_empty_loc[0], elbow_empty_loc[2] = elbow_loc_obj.location[0], elbow_loc_obj.location[2]
                if scn.arp_smart_depth:
                    elbow_empty_loc[1] = elbow_loc_obj.location[1]
                    
            
            # Find the elbow boundaries
            
            if scn.arp_debug_mode:
                print("    Find elbow boundaries...\n")
                
            # Get the arm X angle
            #   opposite angle for the right side
            fac = 1
            if side_idx == 1:
                fac = -1
            
            shoulder_pos = get_object("shoulder_loc"+suff).location            
            hand_pos_plane_x = Vector((hand_marker.location))
            hand_pos_plane_x[1] = 0.0 
            
            shoulder_pos_plane_x = Vector((shoulder_pos))
            shoulder_pos_plane_x[1] = 0.0        
            
            arm_angle_x = Vector((hand_pos_plane_x - shoulder_pos)).angle(Vector((1*fac, 0.0, 0.0)))
            
            mat_angle_x = Matrix.Rotation(-arm_angle_x*fac, 4, 'Y')
            
            # evaluate nearby verts
            clear_selection()
            elbow_selection = []
            has_selected_v = False
            sel_rad = body_width / 20
            
            while has_selected_v == False:
                for v in mesh.verts:
                    if tolerance_check_2(v.co, elbow_empty_loc, 0, 2, sel_rad, side):
                        #v.select = True
                        has_selected_v = True
                        elbow_selection.append(v.index)

                if has_selected_v == False:
                    sel_rad *= 2

            #if side_idx == 1:
            #    print(br)
            
            elbow_back = -1000
            elbow_front = 1000
            vert_up = None
            vert_low = None
            elbow_up = -10000
            elbow_low = 10000

            for v_idx in elbow_selection:
                mesh.verts.ensure_lookup_table()
                vert_y = mesh.verts[v_idx].co[1]
                #front
                if vert_y < elbow_front:
                    elbow_front = vert_y
                # back
                if vert_y > elbow_back:
                    elbow_back = vert_y
                    
                # evaluate the shoulder Z boundaries in the arm space
                vert_z = (mat_angle_x @ mesh.verts[v_idx].co)[2]
                if vert_up == None:
                    vert_up = v_idx
                if vert_low == None:
                    vert_low = v_idx
                if vert_z > elbow_up:
                    elbow_up = vert_z
                    vert_up = v_idx
                if vert_z < elbow_low:
                    elbow_low = vert_z
                    vert_low = v_idx                 
            
            # adust elbow height, in arm space, to better fit the elbow position            
            # get middle elbow point
            p = (mesh.verts[vert_up].co + mesh.verts[vert_low].co) * 0.5
            p[1] = 0.0
            # get arm line points
            line_a = vectorize3(shoulder_empty_loc.copy())
            line_a[1] = 0.0
            line_b = vectorize3(_hand_empty_loc.copy())
            line_b[1] = 0.0
            # project middle point onto the arm line
            p_proj = project_point_onto_line(line_a, line_b, p)
            
            # <!> only apply the evaluated elbow height, if the elbow angle exceeds a given threshold
            # because straight arms are always better for IK chains vector
            elbow_angle = math.degrees((p-line_a).angle(line_b-line_a))
            print("Elbow Angle:", elbow_angle)
            
            elbow_center = elbow_empty_loc.copy()
            
            if not scn.arp_smart_depth or elbow_loc_obj == None:
                if elbow_angle > 3.6:
                    # get the resulting vector
                    vec = p-p_proj
                    elbow_empty_loc += vec
            
                # adjust elbow depth
                elbow_empty_loc[1] = elbow_back + (elbow_front - elbow_back)*0.3            
                elbow_center = elbow_empty_loc.copy()
                elbow_center[1]  = elbow_back + (elbow_front - elbow_back)*0.5
            
            # create the empties
            bpy.ops.object.mode_set(mode='OBJECT')

            create_empty_loc(0.04, shoulder_empty_loc, "shoulder_loc" + side)
            create_empty_loc(0.04, shoulder_base_loc, "shoulder_base_loc" + side)
            create_empty_loc(0.04, elbow_empty_loc, "elbow_loc" + side)

            bpy.ops.object.select_all(action='DESELECT')            

            # FINGERS DETECTION ---------------------------------------------------------------------------------------------

            print("    Find fingers...\n")
            if scn.arp_smart_fingers_engine == 'LEGACY' and scn.arp_fingers_to_detect != 0:
                # Initialize the hand rotation by creating a new hand mesh horizontally aligned
                
                # Z angle
                #print("hand loc temp", hand_loc_temp, "elbow center", elbow_center_temp)        
                global_x_vec = Vector((1.0 * fac, 0.0, 0.0))
                global_y_vec = Vector((0, 1.0 * fac, 0.0))
                
                hand_loc_vec = vectorize3(_hand_empty_loc.copy())
                hand_loc_vec = rotate_point(hand_loc_vec, -arm_angle_x, global_y_vec, shoulder_pos)
                hand_loc_vec[2] = 0.0
                
                elbow_loc_vec = vectorize3(elbow_center.copy())        
                elbow_loc_vec = rotate_point(elbow_loc_vec, -arm_angle_x, global_y_vec, shoulder_pos)
                elbow_loc_vec[2] = 0.0
                        
                forearm_vec = hand_loc_vec - elbow_loc_vec
                       
                forearm_angle_z = forearm_vec.angle(global_x_vec)
                
                if scn.arp_debug_mode:
                    print('      Arm Angle X:', degrees(arm_angle_x))
                    print('      Arm Angle Z:', degrees(forearm_angle_z))
                
                self.arm_angle_x = degrees(arm_angle_x)

                body.hide_select = False
                
                bpy.ops.object.mode_set(mode='OBJECT')
                bpy.ops.object.select_all(action='DESELECT')
                
                body_dupli = duplicate_object(method='data', obj=body, new_name='arp_hand_aligned')
                set_active_object(body_dupli.name)

                body_dupli.parent = get_object('arp_temp_detection')

                # create a selection helper transform
                rot_fac = 1
                if side_idx == 1:
                    rot_fac = -1
                bpy.ops.mesh.primitive_plane_add(size=1, enter_editmode=False, location= hand_marker.location , rotation=(0, arm_angle_x * rot_fac, -forearm_angle_z * rot_fac))
                bpy.context.active_object.name = "arp_hand_transform"
                bpy.context.active_object.parent = get_object("arp_temp_detection")
                hand_transf = get_object("arp_hand_transform")
                matrix_sel = hand_transf.matrix_world
                
                set_active_object("arp_hand_aligned")
                
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='DESELECT')
                mesh = bmesh.from_edit_mesh(bpy.context.active_object.data)

                # select the hand according to the selection helper
                for v in mesh.verts:
                    if side_idx == 0:
                        if (matrix_sel.inverted() @ v.co)[0] < 0.0:
                            v.select = True
                    if side_idx == 1:
                        if (matrix_sel.inverted() @ v.co)[0] > 0.0:
                            v.select = True

                
                # delete other verts
                bpy.ops.mesh.delete(type='VERT')
                
                if scn.arp_debug_mode:
                    print("    Remesh...")
                # Remesh
                bpy.ops.object.mode_set(mode='OBJECT')
                mod = bpy.context.active_object.modifiers.new('remesh', 'REMESH')

                if scn.arp_smart_remesh_type == "type1":
                    mod.mode = 'SMOOTH'
                    # it's best to set the remesh definition according to the mesh actual dimensions
                    if bpy.context.active_object.dimensions[0] < (body_width/3):# generally, t-pose
                        remesh_def = scn.arp_smart_remesh - 2
                    else:# a-pose
                        remesh_def = scn.arp_smart_remesh

                    mod.octree_depth = remesh_def
                    mod.use_remove_disconnected = True
                    mod.threshold = 0.0015

                elif scn.arp_smart_remesh_type == "type2":
                    mod.mode = 'VOXEL'
                    mod.voxel_size = 0.0016 * bpy.context.active_object.dimensions[0] * (1/(scn.arp_smart_remesh/9))
                    mod.adaptivity = 0.0
                
                bpy.ops.object.convert(target='MESH')
                
                # select the closest point to the wrist marker
                if scn.arp_debug_mode:
                    print("    Select closest point to the wrist")
                bpy.ops.object.mode_set(mode='EDIT')
                obj = bpy.context.active_object
                mesh = obj.data
                size = len(mesh.vertices)
                kd = mathutils.kdtree.KDTree(size)

                for vi, v in enumerate(mesh.vertices):
                    kd.insert(v.co, vi)

                kd.balance()

                co, index, dist = kd.find(_hand_empty_loc)

                if index:
                    b_mesh = bmesh.from_edit_mesh(bpy.context.active_object.data)
                    b_mesh.verts.ensure_lookup_table()
                    b_mesh.verts[index].select = True

                    bpy.ops.mesh.select_linked(delimit=set())
                    bpy.ops.mesh.select_all(action='INVERT')

                    bpy.ops.mesh.delete(type='VERT')
                    
                    #   change for cursor
                    scn.tool_settings.transform_pivot_point = 'CURSOR'
                    scn.cursor.location = shoulder_pos

                    bpy.ops.object.mode_set(mode='OBJECT')  
                    
                    #   rotate hand to t-pose
                    rot_angle_x = -arm_angle_x * rot_fac
                    rot_angle_z = forearm_angle_z * rot_fac
                 
                    rotate_object(obj, rot_angle_x, Vector((0,1,0)), shoulder_pos)       
                    bpy.ops.object.mode_set(mode='OBJECT')
                    
                    rotate_object(obj, rot_angle_z, Vector((0,0,1)), vectorize3(elbow_empty_loc)) 
                    bpy.ops.object.mode_set(mode='OBJECT')       
                    
                    rotate_object(hand_transf, rot_angle_z, Vector((0,0,1)), vectorize3(elbow_empty_loc)) 
                    bpy.ops.object.mode_set(mode='OBJECT')
                    
                    rotate_object(hand_transf, rot_angle_x, Vector((0,1,0)), shoulder_pos) 
                    bpy.ops.object.mode_set(mode='OBJECT')
                    
                    bpy.ops.object.select_all(action='DESELECT')        
                    set_active_object(obj.name)
                    
                    bpy.ops.object.transform_apply(location=True, rotation=True, scale=False)
                

                    print("    Detecting fingers", side, "...")

                    bpy.ops.object.select_all(action='DESELECT')
                    set_active_object('hand_loc'+suff)

                    #rotate the marker horizontal
                    def_rotate_value = -arm_angle_x*rot_fac
                    
                    rotate_object(bpy.context.active_object, def_rotate_value, Vector((0,1,0)), shoulder_pos)

                    set_active_object('arp_hand_aligned')
                    hand_dim_x = bpy.context.active_object.dimensions[0]
                    bpy.ops.object.mode_set(mode='EDIT')

                    # smooth a little
                    bpy.ops.mesh.select_all(action='SELECT')
                    bpy.ops.mesh.vertices_smooth(repeat=6, factor=1.0)

                    bpy.ops.mesh.select_all(action='DESELECT')
                    bpy.ops.object.mode_set(mode='OBJECT')
                    hand_obj = get_object("arp_hand_aligned")

                    p_coords=[]

                    if get_object("arp_part_verts"):
                        bpy.data.objects.remove(get_object("arp_part_verts"), do_unlink=True)

                    print("\n    Generating particles...")
                    # create the particles
                    if len(hand_obj.particle_systems) != 0:
                        hand_obj.modifiers.remove(hand_obj.modifiers[0])

                    hand_obj.modifiers.new("part", type='PARTICLE_SYSTEM')
                    bpy.context.evaluated_depsgraph_get().update()
                    hand_obj_eval = bpy.context.evaluated_depsgraph_get().objects.get(hand_obj.name, None)
                    ps = hand_obj.particle_systems[0]
                    """
                    # the depsgraph evaluated object leads to update issues when setting particles params
                    # disable for now
                    if hand_obj_eval:
                        ps = hand_obj_eval.particle_systems[0]
                    else:
                        print("Error, could not evaluate the hand_obj object in depsgraph")
                    """
                    settings = ps.settings
                    settings.frame_start = 0
                    settings.frame_end = 0
                    settings.count = 1600
                    settings.emit_from = 'VOLUME'
                    settings.distribution = 'JIT'
                    settings.physics_type = 'NO'
                    settings.render_type = 'HALO'
                    settings.display_size = 0.005
                    settings.lifetime = 100000

                    # update
                    bpy.ops.object.mode_set(mode='EDIT')
                    bpy.ops.object.mode_set(mode='OBJECT')
                    ps = hand_obj_eval.particle_systems[0]

                    # bake to vertices
                    bpy.ops.mesh.primitive_plane_add(size=100, enter_editmode=False, location=(0, 0, 0), rotation=(0, 0, 0))
                    bpy.ops.object.mode_set(mode='EDIT')
                    bpy.ops.mesh.select_all(action='SELECT')
                    bpy.ops.mesh.delete(type='VERT')
                    bpy.context.active_object.name = "arp_part_verts"
                    arp_part_verts = get_object("arp_part_verts")

                    #   create verts
                    finger_trial = 1
                    b_mesh = bmesh.from_edit_mesh(bpy.context.active_object.data)
                    for p in ps.particles:
                        if p.location != [0,0,0]:# bug, some particles may be in the world center, skip them
                            b_mesh.verts.new(p.location)

                    bpy.ops.mesh.select_all(action='SELECT')
                    bpy.ops.object.mode_set(mode='OBJECT')

                    #   delete particles
                    hand_obj.modifiers.remove(hand_obj.modifiers[0])

                    #   merge to main object
                    bpy.ops.object.select_all(action='DESELECT')
                    set_active_object("arp_part_verts")

                    set_active_object(hand_obj.name)
                    bpy.ops.object.join()

                    bpy.ops.object.mode_set(mode='EDIT')
                    b_mesh = bmesh.from_edit_mesh(bpy.context.active_object.data)
                    particles_vert_loc = [i.co.copy() for i in b_mesh.verts if i.select]

                    # 2 possible trials to help to detect fingers in special cases: first without the "straight thumb" option, second with
                    for finger_detection_trial in [1, 2]:
                        print("\n    [Trial:", finger_detection_trial, ']')

                        print("    Centering particles...")

                        bpy.ops.object.mode_set(mode='EDIT')
                        
                        hand_obj = get_object(bpy.context.active_object.name)
                        b_mesh = bmesh.from_edit_mesh(hand_obj.data)
                        my_tree = BVHTree.FromBMesh(b_mesh)
                        b_mesh.verts.ensure_lookup_table()
                        #hand_transf.rotation_euler = [0,0,0]
                        hand_transf.location = [0,0,0]
                        bpy.context.evaluated_depsgraph_get().update()
                        matrix_sel1 = hand_transf.matrix_world.copy()
                        
                        ray_dir_z = Vector((0,0,100))
                        ray_dir_x = Vector((100,0,0))
                        ray_dir_y = Vector((0,100,0))

                        centering_engine = 1
                        dist_fac = 1
                        
                        # No centering engine for 1 finger detection. Only raycast detection.
                        if scn.arp_fingers_to_detect == 1:
                            centering_engine = -1

                        if centering_engine == 1:
                            # Build the KD Tree used to find the nearest vert to a given one
                            size = len(b_mesh.verts)
                            kd = mathutils.kdtree.KDTree(size)

                            for vi, v in enumerate(b_mesh.verts):
                                kd.insert(v.co, vi)

                            kd.balance()

                            def filter_vert_search(_index):
                                searched_vert = b_mesh.verts[_index]
                                return len(searched_vert.link_edges) > 0 and _index != vert.index

                            vert_to_del = []

                            for vert in b_mesh.verts:
                                for iter in range(0, 7):
                                    if not vert.select or vert in vert_to_del:
                                        continue

                                    # look for the nearest vert on mesh and get its normal
                                    pos, idx, dist = kd.find(vert.co, filter=filter_vert_search)

                                    if pos != None:
                                        v_norm = b_mesh.verts[idx].normal

                                        # Cast a ray from this vert, normal direction
                                        hit, normal, index, distance = my_tree.ray_cast(pos -v_norm*0.0001, -v_norm, 100000)
                                        if hit != None:
                                            vert.co = (hit + pos)/2

                                            # delete verts in the palm
                                            if finger_detection_trial == 1:
                                                y_dir = matrix_sel1 @ Vector((0,1,0))
                                                y_ndir = matrix_sel1 @ Vector((0,-1,0))

                                                y_hit, y_normal, y_index, y_distance = my_tree.ray_cast(vert.co, y_dir, 100000)
                                                ny_hit, ny_normal, ny_index, ny_distance = my_tree.ray_cast(vert.co, y_ndir, 100000)

                                                if y_hit and ny_hit:
                                                    y_magn = y_distance + ny_distance

                                                    dist_max = (dist_fac * (hand_obj.dimensions[1] * scn.arp_finger_thickness)) / 9.0

                                                    if y_magn > dist_max:
                                                        vert_to_del.append(vert)


                                            if finger_detection_trial == 2:
                                                y_dir = matrix_sel1 @ Vector((0,1,0))
                                                y_ndir = matrix_sel1 @ Vector((0,-1,0))
                                                x_dir = matrix_sel1 @ Vector((1,0,0))
                                                x_ndir = matrix_sel1 @ Vector((-1,0,0))

                                                y_hit, y_normal, y_index, y_distance = my_tree.ray_cast(vert.co, y_dir, 100000)
                                                ny_hit, ny_normal, ny_index, ny_distance = my_tree.ray_cast(vert.co, y_ndir, 100000)
                                                x_hit, x_normal, x_index, x_distance = my_tree.ray_cast(vert.co, x_dir, 100000)
                                                nx_hit, nx_normal, nx_index, nx_distance = my_tree.ray_cast(vert.co, x_ndir, 100000)

                                                if y_hit and ny_hit and x_hit and nx_hit:
                                                    y_magn = y_distance + ny_distance
                                                    x_magn = x_distance + nx_distance

                                                    dist_max = (dist_fac * (hand_obj.dimensions[1] * scn.arp_finger_thickness)) / 9.0

                                                    if y_magn > dist_max and x_magn > dist_max:
                                                        vert_to_del.append(vert)
                                    else:
                                        # invalid, no close vert could be found
                                        vert_to_del.append(vert)
                            
                            print("Centered. Remove invalids...")
                            
                            for vert in vert_to_del:
                                b_mesh.verts.remove(vert)
                                
                            print("Removed. Remove doubles...")

                        # Remove double to get a smooth distribution of the vertices
                        hand_obj.data.update()
                        bpy.ops.object.mode_set(mode='OBJECT')
                        bpy.ops.object.mode_set(mode='EDIT')
                        #print("Merge by distance of:", hand_obj.dimensions[0]/40, "hand dim x=", hand_obj.dimensions[0])
                        
                        dist_fac = 40
                        if degrees(forearm_angle_z) > 30:# forearm rotated at high angle leads to longer wrists, then need to shorten dist
                            dist_fac = 60
                            print("    set dist fac", dist_fac)
                            
                        bpy.ops.mesh.remove_doubles(threshold=hand_obj.dimensions[0]/dist_fac)
                        
                        print("Removed.")
                        
                        def get_index(list, value):
                            # return the index of a vertice from its position
                            for _i, j in enumerate(list):
                                if j == value:
                                    return _i
                       
                        # Separate the longer finger tip vertice as a new vert, if fingers to detect == 1 or 2
                        if scn.arp_fingers_to_detect == 1 or scn.arp_fingers_to_detect == 2:
                            print("Separate longer finger tip...")
                            b_mesh = bmesh.from_edit_mesh(bpy.context.active_object.data)
                            b_mesh.verts.ensure_lookup_table()
                            vert_coords1 = []
                            for vert in b_mesh.verts:
                                vert_coords1.append(Vector((vert.co[0], vert.co[1], vert.co[2])))

                            # Get the longer finger tip
                            coords_sorted1 = sorted(vert_coords1, reverse=True, key=itemgetter(0))
                            if side_idx == 1:
                                coords_sorted1 = sorted(vert_coords1, reverse=False, key=itemgetter(0))

                            # Copy the vert (original is deleted after)
                            new_vert = b_mesh.verts.new(coords_sorted1[0])
                            new_vert.select = True

                        if scn.arp_debug_mode:
                            print("\n    Creating edges...")

                        hand_obj = get_object(bpy.context.active_object.name)

                        # separate verts into a new object
                        if get_object("arp_part_verts") == None:
                            bpy.ops.object.mode_set(mode='EDIT')

                            try:
                                bpy.ops.mesh.separate(type="SELECTED")
                                bpy.ops.object.mode_set(mode='OBJECT')
                                current_obj = bpy.context.active_object.name
                                bpy.ops.object.select_all(action='DESELECT')
                                set_active_object(current_obj+".001")
                                bpy.context.active_object.name = "arp_part_verts"

                            except:# Error, no vertices have been generated. Probably due to wrong fingers detection amount (look for 5 fingers for mittens or box gloves instead of 1...)
                                print("    Fingers detection on side", side, "failed, particle generation failed. Probably due to wrong fingers detection parameters (look for 5 fingers instead of 1...)")
                                if side_idx == 0:
                                    self.fingers_detection_success_l = False
                                if side_idx == 1:
                                    self.fingers_detection_success_r = False

                        else:
                            set_active_object("arp_part_verts")

                        if (self.fingers_detection_success_l and side_idx == 0) or (self.fingers_detection_success_r and side_idx == 1):
                            obj = bpy.context.active_object
                            # keep only vertices
                            bpy.ops.object.mode_set(mode='EDIT')
                            bpy.ops.mesh.select_all(action='SELECT')
                            bpy.ops.mesh.delete(type='EDGE_FACE')
                            bpy.ops.mesh.select_all(action='DESELECT')

                            b_mesh = bmesh.from_edit_mesh(bpy.context.active_object.data)
                            b_mesh.verts.ensure_lookup_table()

                            fingers_total = scn.arp_fingers_to_detect
                            restrict_edgify_half_hand = False
                            if fingers_total <= 2:
                                restrict_edgify_half_hand = True

                            # Build the vertices coords list (centered verts cloud, if more than 2 fingers to detect)
                            vert_coords = []
                            b_mesh.verts.ensure_lookup_table()
                            for vert in b_mesh.verts:
                                vert_coords.append(matrix_sel1.inverted() @ Vector((vert.co[0], vert.co[1], vert.co[2])))
                            
                            # Get the longer finger tip
                                # Sort the list by X values to get the right boundary vert
                            coords_sorted = sorted(vert_coords, reverse=True, key=itemgetter(0))
                            if side_idx == 1:
                                coords_sorted = sorted(vert_coords, reverse=False, key=itemgetter(0))

                                # Get the index in the actual vert list
                            vert_tip = get_index(vert_coords, coords_sorted[0])

                            if scn.arp_debug_mode:
                                print("    vert_tip", vert_tip, coords_sorted[0])
                            
                            bpy.ops.mesh.select_all(action='DESELECT')
                            b_mesh.verts[vert_tip].select = True

                            first_finger_tip = vert_tip

                            if scn.arp_debug_mode:
                                print("    Found first finger vert", vert_tip)
                            
                            # Create edges between verts
                            #   build the KD Tree used to find the nearest vert to a given one
                            size = len(b_mesh.verts)
                            kd = mathutils.kdtree.KDTree(size)

                            for vert_tip, v in enumerate(b_mesh.verts):
                                kd.insert(v.co, vert_tip)

                            kd.balance()
                            
                            def get_connected_vert(vert=None, exclude=None):
                                sel_edge = 0
                                if len(vert.link_edges) > 1:
                                    if vert.link_edges[sel_edge].verts[0] == exclude or vert.link_edges[sel_edge].verts[1] == exclude:
                                        sel_edge = 1

                                if vert.link_edges[sel_edge].verts[0] != vert:
                                    return vert.link_edges[sel_edge].verts[0]
                                else:
                                    return vert.link_edges[sel_edge].verts[1]

                            def edgify(starting_vert):
                                count = 0
                                dist_max = bpy.context.active_object.dimensions[0] * 0.2
                                if finger_detection_trial == 2:
                                    dist_max = hand_dim_x/10# this helps in case the thumb is straight, generally giving longer distances

                                angle_max = 50#50
                                current_vert = starting_vert
                                draw_segment = True
                                edge_dir = "to_root"
                                tip_index = None
                                root_index = None

                                while draw_segment:                          
                                    def filter_vert_search(_index):
                                        searched_vert = b_mesh.verts[_index]
                                        if side_idx == 0:
                                            dir_compare1 = searched_vert.co[0] < current_vert.co[0]
                                            dir_compare2 = searched_vert.co[0] > current_vert.co[0]
                                        if side_idx == 1:# reverse the direction for the right side
                                            dir_compare1 = searched_vert.co[0] > current_vert.co[0]
                                            dir_compare2 = searched_vert.co[0] < current_vert.co[0]

                                        if len(searched_vert.link_edges) == 0 and _index != current_vert.index and ((edge_dir == "to_root" and dir_compare1) or (edge_dir == "to_tip" and dir_compare2)):
                                            if current_vec != None:
                                                fac = 1
                                                #if edge_dir == "to_tip":
                                                #    fac = 1

                                                vec_angle = (fac * current_vec).angle(searched_vert.co - current_vert.co)

                                                if vec_angle < math.radians(angle_max):
                                                    return True
                                            else:
                                                return True

                                        return False


                                    def filter_vert_search_2(_index):
                                        searched_vert = b_mesh.verts[_index]
                                        if side_idx == 0:
                                            dir_compare1 = searched_vert.co[0] < current_vert.co[0]
                                            dir_compare2 = searched_vert.co[0] > current_vert.co[0]
                                        if side_idx == 1:# reverse the direction for the right side
                                            dir_compare1 = searched_vert.co[0] > current_vert.co[0]
                                            dir_compare2 = searched_vert.co[0] < current_vert.co[0]

                                        if len(searched_vert.link_edges) == 0 and _index != current_vert.index and _index != first_iter_vert and ((edge_dir == "to_root" and dir_compare1) or (edge_dir == "to_tip" and dir_compare2)):

                                            if current_vec:
                                                fac = 1
                                                #if edge_dir == "to_tip":
                                                #    fac = 1

                                                vec_angle = (fac * current_vec).angle(searched_vert.co - current_vert.co)

                                                if vec_angle < math.radians(angle_max):
                                                    return True
                                            else:
                                                return True

                                        return False

                                    # calculate previous edge vector for angle check
                                    current_vec = None
                                    if len(current_vert.link_edges) > 0:
                                        vert2 = get_connected_vert(current_vert, current_vert)
                                        current_vec = current_vert.co - vert2.co

                                    #else:
                                    #    current_vec = Vector((-1,0,0))

                                    # find nearest vert
                                        # 2 iteration: if the second angle is lower, choose this one
                                        # 1st
                                    pos, idx, dist = kd.find(current_vert.co, filter=filter_vert_search)


                                    #   2nd
                                    if idx != None:
                                        if current_vec == None:# first vertice, set the vec to X
                                            current_vec = Vector((-1,0,0))

                                        first_iter_vert = idx

                                        vec1_angle = current_vec.angle(pos - current_vert.co)

                                        pos2, idx2, dist2 = kd.find(current_vert.co, filter=filter_vert_search_2)

                                        if pos2:
                                            vec2_angle = current_vec.angle(pos2 - current_vert.co)
                                            angle_diff = degrees(vec1_angle) - degrees(vec2_angle)

                                            if dist2 < dist_max and angle_diff > 5:#5
                                                # valid vertices, choose this one
                                                # take into account the non chosen vert as a new edge if it's closer
                                                if dist2 > dist:
                                                    count += 1
                                                    #print("Adding 1 additional edge count")

                                                invalid_verts.append(idx)
                                                pos, idx, dist = pos2, idx2, dist2


                                    chosen_vert = None
                                    shortest_dist = None

                                    if pos:
                                        continue_edge = False

                                        if not restrict_edgify_half_hand:

                                            if dist < dist_max:
                                                continue_edge = True

                                        if restrict_edgify_half_hand:
                                            if side_idx == 0:
                                                if dist < dist_max and pos[0] > (coords_sorted[0][0] + coords_sorted[len(coords_sorted)-1][0])/2:
                                                    continue_edge = True

                                            if side_idx == 1:
                                                if dist < dist_max and pos[0] < (coords_sorted[0][0] + coords_sorted[len(coords_sorted)-1][0])/2:
                                                    continue_edge = True

                                        if continue_edge:
                                            chosen_vert = idx

                                            if chosen_vert != None:
                                                # Create edge
                                                b_mesh.verts.ensure_lookup_table()
                                                b_mesh.verts[chosen_vert].select = True

                                                b_mesh.edges.new((b_mesh.verts[chosen_vert], current_vert))
                                                current_vert = b_mesh.verts[chosen_vert]
                                                count += 1


                                        else:# reached the end of the segment
                                            if edge_dir == "to_root":
                                                edge_dir = "to_tip"

                                                root_index = current_vert.index
                                                current_vert = starting_vert
                                            else:
                                                draw_segment = False
                                                tip_index = current_vert.index

                                    else:# reached the end of the segment
                                        if edge_dir == "to_root":
                                            edge_dir = "to_tip"

                                            root_index = current_vert.index
                                            current_vert = starting_vert
                                        else:
                                            draw_segment = False
                                            tip_index = current_vert.index


                                return count, root_index, tip_index


                            # Vertice filter search function -------------------------------------------------------
                            finger_thickness = bpy.context.active_object.dimensions[1]/20

                            def search_left_only(_index):
                                searched_vert = b_mesh.verts[_index]
                                dir_compare = (searched_vert.co)[0] > (root_vert.co)[0]
                                if side_idx == 1:
                                    dir_compare = (searched_vert.co)[0] < (root_vert.co)[0]

                                return len(searched_vert.link_edges) == 0 and _index != current_vert.index and (searched_vert.co)[1] > (current_vert.co)[1]+finger_thickness and dir_compare and not _index in invalid_verts

                            def search_right_only(_index):
                                searched_vert = b_mesh.verts[_index]
                                return len(searched_vert.link_edges) == 0 and _index != current_vert.index and (searched_vert.co)[1] < (current_vert.co)[1]-finger_thickness and not _index in invalid_verts

                            def search_up_only(_index):
                                searched_vert = b_mesh.verts[_index]
                                dir_compare = (searched_vert.co)[0] < (current_vert.co)[0]
                                if side_idx == 1:
                                    dir_compare = (searched_vert.co)[0] > (current_vert.co)[0]

                                return _index != current_vert.index and dir_compare and not _index in invalid_verts# and len(searched_vert.link_edges) == 0


                            invalid_verts = []
                            
                            # Start processing, first finger (longer)
                            found_first_finger = False
                            current_vert = b_mesh.verts[first_finger_tip]
                            auto_align_phalanges = False
                            hand_pos_vec = Vector((get_object("hand_loc"+suff).location[0], (wrist_bound_back+wrist_bound_front)/2, get_object("hand_loc"+suff).location[2]))     
                            hand_pos_offset = hand_pos_vec.copy()
                            hand_pos_vec = rotate_point(hand_pos_vec, rot_angle_z, Vector((0,0,1)), vectorize3(elbow_empty_loc))
                            hand_pos_offset = hand_pos_vec - hand_pos_offset
                            
                            if fingers_total <= 2:
                                auto_align_phalanges = True

                            if auto_align_phalanges:
                                print("Auto align phalanges...")
                                #print(br)
                                root_pos = (current_vert.co + hand_pos_vec) * 0.5
                                root_vert = b_mesh.verts.new(root_pos)
                                b_mesh.verts.index_update()

                                last_vert = current_vert
                                cast_object = get_object("arp_hand_aligned")
                                
                                if scn.arp_debug_mode:
                                    print('create verts and edges aligned toward the wrist')
                                    
                                # create verts and edges aligned toward the wrist
                                for y in range(1,3):
                                    finger_vec = (root_pos- current_vert.co)
                                    vloc = current_vert.co + (finger_vec/3.5) * y

                                    # Find the Z pos
                                    have_hit_top = have_hit_bot = False
                                    ray_dir = Vector((0,0,1000000))
                                    ray_dir_neg = 1
                                    ori = Vector((vloc[0], vloc[1], vloc[2] + 2000))
                                    ori_base = ori.copy()
                                    offset = bpy.context.active_object.dimensions[2]*0.005                   
        
                                    maxi = 10000
                                    iter = 0
                                    trial = 0
                                    
                                    while not have_hit_top and iter < maxi:    
                                        cast_object_eval = bpy.context.evaluated_depsgraph_get().objects.get(cast_object.name, None)
                                        sucess1, hit_top, normal, index = cast_object_eval.ray_cast(ori, -ray_dir, distance=ray_dir.magnitude)
                                        if not sucess1:
                                            if trial == 0:
                                                if iter < 5000:# there's a hole in the mesh, offset the Y position
                                                    ori[1] += bpy.context.active_object.dimensions[1]*0.0001
                                                else:# try other direction
                                                    iter = 0
                                                    ori = ori_base.copy()
                                                    ray_dir_neg = -1
                                                    trial = 1
                                                    
                                            elif trial == 1:
                                                if iter < 5000:# there's a hole in the mesh, offset the Y position
                                                    ori[1] -= bpy.context.active_object.dimensions[1]*0.0001
                                        else:
                                            if scn.arp_debug_mode:
                                                print("Success top")
                                            have_hit_top = True
                                            iter = 0
                                            
                                            while not have_hit_bot and iter < maxi:
                                                success2, hit_bot, normal, index = cast_object_eval.ray_cast(hit_top + Vector((0,0, -offset)), -ray_dir, distance=ray_dir.magnitude)
                                                if not success2:# there's a hole in the mesh, offset the Y position
                                                    hit_top[1] += bpy.context.active_object.dimensions[1]*0.0001*ray_dir_neg

                                                else:
                                                    if scn.arp_debug_mode:
                                                        print("Success bot")
                                                    vloc[2] = (hit_top[2] + hit_bot[2])*0.5
                                                    have_hit_bot = True
                                                iter += 1
                                                
                                        iter += 1
                                    
                                    if scn.arp_debug_mode:
                                        print("Terminated while")
                                        
                                    # Create the vert
                                    new_vert = b_mesh.verts.new(vloc)
                                    b_mesh.verts.index_update()
                                    # Create edge
                                    b_mesh.edges.new((last_vert, new_vert))
                                    last_vert = new_vert

                                if scn.arp_debug_mode:
                                    print("Final edge...")
                                    
                                # Final edge
                                b_mesh.edges.new((last_vert, root_vert))
                                b_mesh.verts.ensure_lookup_table()

                                root_idx = root_vert.index
                                tip_idx = first_finger_tip

                                found_first_finger = True
                                
                                if scn.arp_debug_mode:
                                    print("Found first finger", root_vert.index)


                            iterate = 0
                            failed_to_find_first_finger = False

                            while not found_first_finger:
                                edge_count, root_idx, tip_idx = edgify(b_mesh.verts[first_finger_tip])

                                if edge_count < 3:
                                    if scn.arp_debug_mode:
                                        print("    Could not edgify the first finger, try again...")

                                    # Find another close vert
                                    invalid_verts.append(root_idx)
                                    invalid_verts.append(first_finger_tip)
                                    pos, idx, dist = kd.find(b_mesh.verts[first_finger_tip].co, filter=search_up_only)

                                    if idx != None:
                                        first_finger_tip = idx
                                    # Fail to find, exit detection
                                    if idx == None or iterate > 79:
                                        if finger_detection_trial == 1:
                                            print("    Fingers detection on side", side, "failed, try again with straight thumb option")
                                            # delete verts used for detection
                                            print("    deleting current detection...")
                                            bpy.ops.object.mode_set(mode='OBJECT')
                                            bpy.data.objects.remove(get_object("arp_part_verts"), do_unlink=True)
                                            # restore original particles states
                                            print("    restoring initial data...")
                                            set_active_object("arp_hand_aligned")
                                            bpy.ops.object.mode_set(mode='EDIT')
                                            b_mesh = bmesh.from_edit_mesh(bpy.context.active_object.data)
                                            for vloc in particles_vert_loc:
                                                nv = b_mesh.verts.new(vloc)
                                                nv.select = True

                                            failed_to_find_first_finger = True
                                            break

                                        if finger_detection_trial == 2:
                                            print("    Fingers detection on side", side, "failed")
                                            if side_idx == 0:
                                                self.fingers_detection_success_l = False
                                            if side_idx == 1:
                                                self.fingers_detection_success_r = False

                                            break

                                else:
                                    found_first_finger = True
                                    if scn.arp_debug_mode:
                                        print("    Found first finger", root_idx)
                                        
                                iterate += 1

                            go_upper = True
                            go_lower = True

                            if failed_to_find_first_finger:
                                continue# second trial

                        if (self.fingers_detection_success_l and side_idx == 0) or (self.fingers_detection_success_r and side_idx == 1):
                            b_mesh.verts.ensure_lookup_table()

                            # Finger list format: ("name", tip index, root index, tip coords, root coords)
                            fingers_list = [("finger0", tip_idx, root_idx, b_mesh.verts[tip_idx].co.copy(), b_mesh.verts[root_idx].co.copy())]

                            if fingers_total <= 2:
                                go_upper = False
                                go_lower = False

                            # Find upper tips
                            if scn.arp_debug_mode:
                                if go_upper:
                                    print("\n    Going up")

                            go_upper_count = 0
                            current_vert = b_mesh.verts[tip_idx]
                            root_vert = b_mesh.verts[root_idx]

                            while go_upper:
                                go_upper_count += 1
                                pos, idx, dist = kd.find(current_vert.co, filter=search_left_only)

                                if idx != None:
                                    b_mesh.verts[idx].select = True
                                   # Edgify
                                    edge_count, root_idx, tip_idx = edgify(b_mesh.verts[idx])
                                    if edge_count < 4:
                                        if scn.arp_debug_mode:
                                            print("    Finger", go_upper_count, "is invalid finger, not enough edges detected")
                                        invalid_verts.append(idx)
                                        invalid_verts.append(root_idx)
                                    else:
                                        if scn.arp_debug_mode:
                                            print("    Found finger", go_upper_count, tip_idx)

                                        fingers_list.append(("finger"+str(go_upper_count), tip_idx, root_idx, b_mesh.verts[tip_idx].co.copy(), b_mesh.verts[root_idx].co.copy()))
                                        current_vert = b_mesh.verts[tip_idx]
                                        root_vert = b_mesh.verts[root_idx]

                                else:
                                    go_upper = False

                                 # if found all fingers, exit
                                if len(fingers_list) == fingers_total:
                                    go_upper = False
                                    go_lower = False


                            # Go Lower
                            if scn.arp_debug_mode:
                                if go_lower:
                                    print("\n    Going down")

                            go_lower_count = 0

                            while go_lower:
                                current_vert = b_mesh.verts[first_finger_tip]
                                go_lower_count += 1
                                pos, idx, dist = kd.find(current_vert.co, filter=search_right_only)

                                if idx != None:
                                    b_mesh.verts[idx].select = True

                                   # Edgify
                                    edge_count, root_idx, tip_idx = edgify(b_mesh.verts[idx])

                                    if edge_count < 5:
                                        bpy.ops.mesh.select_all(action='DESELECT')
                                        b_mesh.verts[idx].select = True
                                        bpy.ops.mesh.select_linked(delimit=set())
                                        bpy.ops.mesh.delete(type='EDGE_FACE')

                                        if scn.arp_debug_mode:
                                            print("    Finger", go_lower_count, "is invalid finger, not enough edges detected")

                                    else:
                                        if scn.arp_debug_mode:
                                            print("    Found finger", go_lower_count, tip_idx)

                                        fingers_list.append(("finger"+str(go_lower_count), tip_idx, root_idx, b_mesh.verts[tip_idx].co.copy(), b_mesh.verts[root_idx].co.copy()))
                                        current_vert = b_mesh.verts[tip_idx]

                                else:
                                    go_lower = False

                                if go_lower_count > 30:
                                    go_lower = False

                                # if found all fingers, exit
                                if len(fingers_list) == fingers_total:
                                    go_lower = False


                            # Delete vertices not connected to edges within the fingers thickness value to avoid issues
                            def find_connected_verts(_index):
                                searched_vert = b_mesh.verts[_index]
                                if (searched_vert.co - vert.co).magnitude < finger_thickness:
                                    if len(searched_vert.link_edges) > 0:
                                        return True

                                return False

                            b_mesh.verts.ensure_lookup_table()

                            for vert in b_mesh.verts:
                                if len(vert.link_edges) == 0:
                                    pos, idx, dist = kd.find(vert.co, filter=find_connected_verts)
                                    if idx != None and not idx in invalid_verts:
                                        invalid_verts.append(vert.index)
                                        if scn.arp_debug_mode:
                                            print("    APPENDING INVALID", vert.index)

                            # If some fingers haven't been found yet, try again, it's probably the thumb wich is in a tricky place
                            while len(fingers_list) < fingers_total:
                                print("\n    Look for the thumb...")
                                # Look for the bottom vert not linked to edge
                                bot_bound = None
                                thumb_tip = None

                                if fingers_total != 2:
                                    for vert in b_mesh.verts:
                                        if not vert.index in invalid_verts:

                                            if len(vert.link_edges) == 0:
                                                coord = vert.co.copy()

                                                if bot_bound == None:
                                                    bot_bound = coord[1]
                                                    thumb_tip = vert
                                                else:
                                                    thumb_tip_coord = thumb_tip.co.copy()

                                                    if coord[1] < bot_bound:
                                                        if (coord[0] > thumb_tip_coord[0] and side_idx == 0) or (coord[0] < thumb_tip_coord[0] and side_idx == 1):
                                                            bot_bound = coord[1]
                                                            thumb_tip = vert

                                if fingers_total == 2:
                                    for vert in b_mesh.verts:
                                        if not vert.index in invalid_verts:

                                            if len(vert.link_edges) == 0:
                                                coord = vert.co.copy()

                                                if thumb_tip == None:
                                                    thumb_tip = vert
                                                else:
                                                    thumb_tip_coord = thumb_tip.co.copy()

                                                    if coord[1] < thumb_tip_coord[1]:
                                                        thumb_tip = vert

                                if thumb_tip:
                                    bpy.ops.mesh.select_all(action='DESELECT')

                                    thumb_tip.select = True
                                    restrict_edgify_half_hand = False
                                    edge_count, root_idx, tip_idx = edgify(thumb_tip)

                                    if edge_count < 3:
                                        if scn.arp_debug_mode:
                                            print("    Thumb is invalid finger, not enough edges detected")
                                        invalid_verts.append(root_idx)
                                    else:
                                        if scn.arp_debug_mode:
                                            print("    Found thumb", tip_idx)
                                        fingers_list.append(("thumb", tip_idx, root_idx, b_mesh.verts[tip_idx].co.copy(), b_mesh.verts[root_idx].co.copy()))

                                else:
                                    if finger_detection_trial == 1:
                                        print("    Fingers detection on side", side, "failed, try again with straight thumb option")
                                        # delete verts used for detection
                                        print("    deleting current detection...")
                                        bpy.ops.object.mode_set(mode='OBJECT')
                                        bpy.data.objects.remove(get_object("arp_part_verts"), do_unlink=True)
                                        # restore original particles states
                                        print("    restoring initial data...")
                                        set_active_object("arp_hand_aligned")
                                        bpy.ops.object.mode_set(mode='EDIT')
                                        b_mesh = bmesh.from_edit_mesh(bpy.context.active_object.data)
                                        for vloc in particles_vert_loc:
                                            #print("set vertex", vloc)
                                            nv = b_mesh.verts.new(vloc)
                                            nv.select = True

                                        break

                                    elif finger_detection_trial == 2:
                                        print("    Fingers detection on side", side, "failed")
                                        if side_idx == 0:
                                            self.fingers_detection_success_l = False
                                        if side_idx == 1:
                                            self.fingers_detection_success_r = False
                                        break


                            if len(fingers_list) == fingers_total:
                                break

                    if (self.fingers_detection_success_l and side_idx == 0) or (self.fingers_detection_success_r and side_idx == 1):

                        print("    Fingers", side, "have been fully detected")
                        
                        # Re order from top to bottom, based on Y position
                        fingers_list = sorted(fingers_list, reverse=True, key=lambda x: x[3][1])

                        if fingers_total != 2:
                            # make sure the smaller X value is the thumb
                            if side_idx == 0:
                                fingers_x_sort = sorted(fingers_list, reverse=False, key=lambda x: x[3][0])                   
                            if side_idx == 1:# revert order for the right side
                                fingers_x_sort = sorted(fingers_list, reverse=True, key=lambda x: x[3][0])

                            
                            thumb_index = fingers_list.index(fingers_x_sort[0])
                          
                            if thumb_index > 1:# avoid confusion with pinky/ring
                                fingers_list.pop(thumb_index)
                                fingers_list.insert(len(fingers_list), fingers_x_sort[0])                    
                            else:
                                print("    Skip thumb re-order, could be pinky or ring")
                                

                        
                        # Rename the fingers according to the sorted list
                        fingers_names = ["pinky", "ring", "middle", "index", "thumb"]

                        if fingers_total == 4:# remove the index
                            fingers_names = ["pinky", "ring", "middle", "thumb"]
                        if fingers_total == 3:
                            fingers_names = ["pinky", "ring", "thumb"]
                        if fingers_total == 2:
                            fingers_names = ["index", "thumb"]
                        if fingers_total == 1:
                            fingers_names = ["index"]
                            
                        #print("fingers_names", fingers_names)

                        for fi, name in enumerate(fingers_names):
                            #print(fingers_list[fi][0])
                            fingers_list[fi] = (name, fingers_list[fi][1], fingers_list[fi][2], fingers_list[fi][3], fingers_list[fi][4])
                      
                        #print("fingers_list", fingers_list)
                        # Ensure the tip vert reaches the tip mesh surface
                        for fi, finger in enumerate(fingers_list):
                            vert_idx = finger[1]
                            current_vert = b_mesh.verts[vert_idx]
                            vert2 = get_connected_vert(current_vert, current_vert)
                            ray_dir = vert2.co - current_vert.co
                            hand_obj_eval = bpy.context.evaluated_depsgraph_get().objects.get(hand_obj.name, None)
                            hit, loc, norm, face = hand_obj_eval.ray_cast(current_vert.co, -ray_dir)
                            if hit:
                                current_vert.co = loc
                                # update the fingers list
                                fingers_list[fi] = (fingers_list[fi][0], fingers_list[fi][1], fingers_list[fi][2], loc, fingers_list[fi][4])


                        # resample at a higher rate for better phalanges position
                        bpy.ops.mesh.select_all(action='SELECT')
                        bpy.ops.mesh.subdivide(smoothness=0)
                        if fingers_total <= 2:
                            bpy.ops.mesh.subdivide(smoothness=0)
                        b_mesh.verts.ensure_lookup_table()


                        # get the fingers length
                        fingers_length = []
                        b_mesh.edges.ensure_lookup_table()

                        for fi, finger in enumerate(fingers_list):
                            current_vert = b_mesh.verts[finger[1]]
                            previous_vert = None
                            total_length = 0.0
                            progress = True
                            start = True

                            while progress:
                                if len(current_vert.link_edges) > 1 or start == True:# break the loop if the end is reached

                                    new_vert = get_connected_vert(vert=current_vert, exclude=previous_vert)
                                    previous_vert = current_vert
                                    current_vert = new_vert

                                    total_length += (previous_vert.co-current_vert.co).magnitude
                                    start = False

                                else:
                                    progress = False

                                    fingers_length.append(total_length)

                        if scn.arp_debug_mode:
                            print("\n    Fingers length:")
                            for fi in fingers_length:
                                print("    ", fi)

                        # Place the phalanges
                        #print("    Phalanges...")
                        phalanges_pos = []

                        # find the phalanges pos
                        for fi, finger in enumerate(fingers_list):
                            current_vert = b_mesh.verts[finger[1]]
                            previous_vert = None
                            current_length = 0.0
                            total_length = fingers_length[fi]
                            progress = True
                            start = True
                            found_phal_1 = False
                            found_phal_2 = False

                            while progress:

                                if len(current_vert.link_edges) > 1 or start == True:# break the loop if the end is reached

                                    new_vert = get_connected_vert(vert=current_vert, exclude=previous_vert)
                                    previous_vert = current_vert
                                    current_vert = new_vert

                                    current_length += (previous_vert.co-current_vert.co).magnitude
                                    start = False

                                    if current_length >= total_length/3 and found_phal_1 == False:
                                        found_phal_1 = True
                                        phalanges_pos.append((finger[0], current_vert.co.copy()))


                                    if current_length >= (total_length/3)*2 and found_phal_2 == False:
                                        found_phal_2 = True
                                        progress = False
                                        if not finger[0] == "thumb":
                                            phalanges_pos.append((finger[0], current_vert.co.copy()))

                                        else:# for the thumb, the root is the 2nd phalange
                                            phalanges_pos.append((finger[0], finger[4]))

                                else:
                                    progress = False
                                    fingers_length.append(total_length)



                        # Place the fingers master root
                        #print("\n    Root positions...")
                        fingers_root_list = []
                        
                        # get wrist center
                        wrist_bound_back = wrist_bound_back + (wrist_bound_front-wrist_bound_back) * 0.3                
                        wrist_bound_front = wrist_bound_front + (wrist_bound_back-wrist_bound_front) * 0.3
                        
                        # move to t-pose
                        wrist_bound_back += hand_pos_offset[1]
                        wrist_bound_front += hand_pos_offset[1]
                        
                        wrist_vec = wrist_bound_front-wrist_bound_back      
                        
                        for fi, finger in enumerate(fingers_list):
                            if finger[0] != "thumb":                      
                                pos = hand_pos_vec + (finger[4] - hand_pos_vec) * 0.3                                       
                                pos[1] = (finger[4][1] + (wrist_bound_back + wrist_vec * fi * 0.25)) * 0.5
                            else:
                                pos = (finger[4] + hand_pos_vec) * 0.5

                            fingers_root_list.append((finger[0]+"_root", pos))
                            

                        # Refine pass 1: smoothen the wrist-fingers root distance
                        average_dist = 0.0
                        count = 0
                        for fi, finger in enumerate(fingers_list):
                            if finger[0] == "pinky" or finger[0] == "ring" or finger[0] == "middle" or finger[0] == "index":
                                average_dist += (hand_pos_vec - fingers_list[fi][4]).magnitude
                                count += 1

                        if len(fingers_list) > 2:
                            average_dist /= count
                        else:
                            average_dist = (fingers_list[0][4] - hand_pos_vec).magnitude

                        # dict storing the root original pos and reposition vec
                        root_move_vec = {}

                        for fi, finger in enumerate(fingers_list):
                            if finger[0] != "thumb":
                                dir = (fingers_list[fi][4] - hand_pos_vec).normalized()
                                pos = hand_pos_vec + dir * average_dist * 0.9# 0.9 to move them back a little, they're generally too forward
                                root_move_vec[finger[0]] = (fingers_list[fi][4], pos - fingers_list[fi][4])
                                fingers_list[fi] = (fingers_list[fi][0], fingers_list[fi][1], fingers_list[fi][2], fingers_list[fi][3], pos)


                        # Refine pass 2: re-position the phalanges
                        for fi in range(0, len(phalanges_pos), 2):
                            finger_name = phalanges_pos[fi+1][0]
                            if finger_name != "thumb":
                                phal1_pos = phalanges_pos[fi+1][1]
                                phal1_vec = root_move_vec[finger_name][0] - phal1_pos
                                d = (root_move_vec[finger_name][1].magnitude)*0.4
                                d = clamp_max(d, phal1_vec.magnitude)
                                phal1_pos = phal1_pos + phal1_vec.normalized()*d

                                # update the phalange list
                                phalanges_pos[fi+1] = (phalanges_pos[fi+1][0], phal1_pos)                       

                        # Create an empty for detected position
                        #print("    Create empties loc...")
                        bpy.ops.object.mode_set(mode='OBJECT')
                        
                        for f_i, finger in enumerate(fingers_list):
                            # tip
                            create_empty_loc(0.02, finger[3], finger[0] + "_top"+side)

                            # root
                            create_empty_loc(0.02, finger[4], finger[0] + "_bot"+side)

                            # master root
                            create_empty_loc(0.02, fingers_root_list[f_i][1], fingers_root_list[f_i][0]+side)

                        for fi in range(0, len(phalanges_pos), 2):
                            # phalange 1
                            create_empty_loc(0.02, phalanges_pos[fi][1], phalanges_pos[fi][0] + "_phal_1"+side)
                     
                            # phalange 2
                            create_empty_loc(0.02, phalanges_pos[fi+1][1], phalanges_pos[fi+1][0] + "_phal_2"+side)
                        
                    
                    # --End if scn.arp_fingers_to_detect != 0
                    bpy.ops.object.mode_set(mode='OBJECT')

                    # rotate the empties back to original coords
                    scn.cursor.location = shoulder_pos
                    bpy.ops.object.select_all(action='DESELECT')
                    
                    rot_angle_x = arm_angle_x * rot_fac
                    rot_angle_z = -forearm_angle_z * rot_fac
                    for obj in get_object("auto_detect_loc").children:
                        if ("pinky" in obj.name or "ring" in obj.name or "middle" in obj.name or "index" in obj.name or "thumb" in obj.name) and side in obj.name:
                            rotate_object(obj, rot_angle_z, Vector((0,0,1)), vectorize3(elbow_empty_loc))
                            bpy.ops.object.mode_set(mode='OBJECT')
                            rotate_object(obj, rot_angle_x, Vector((0,1,0)), shoulder_pos)                               
                           
                    rotate_object(get_object('hand_loc'+suff), rot_angle_x, Vector((0,1,0)), shoulder_pos)   

                    bpy.ops.object.mode_set(mode='OBJECT')
                    
                    #delete arp_hand_aligned
                    bpy.data.objects.remove(get_object("arp_hand_aligned"), do_unlink=True)

                    # delete arp_part_verts objects
                    if get_object("arp_part_verts"):
                        bpy.data.objects.remove(get_object("arp_part_verts"), do_unlink=True)

                    # delete the selection helper
                    if get_object("arp_hand_transform"):
                        bpy.data.objects.remove(get_object("arp_hand_transform"), do_unlink=True)
                        
                else:
                    print("Too low poly, could not find the wrist vertices")
                    scn.arp_fingers_to_detect = 0
             
            if bpy.context.active_object:
                bpy.ops.object.mode_set(mode='OBJECT')
            
            create_empty_loc(0.04, _hand_empty_loc, "hand_loc"+side)

        # Legs detection -------------------------------------------------------------------------

        foot_loc_l = get_object("foot_loc")
        foot_loc_r = get_object("foot_loc_sym")

        foot_markers = [foot_loc_l]

        if not scn.arp_smart_sym:
            foot_markers.append(foot_loc_r)


        for side_idx, foot_marker in enumerate(foot_markers):

            if side_idx == 0:
                print('\n[Left foot detection...]')
            if side_idx == 1:
                print('\n[Right foot detection...]')

            side = ".l"
            if side_idx == 1:
                side = ".r"

            set_active_object(body.name)
            bpy.ops.object.mode_set(mode='EDIT')

            #select vertices around the foot_loc
            selected_index = []
            mesh = bmesh.from_edit_mesh(bpy.context.active_object.data)


            for v in mesh.verts:
                compare_x = v.co[0] > 0
                if side_idx == 1:
                    compare_x = v.co[0] < 0
                if v.co[2] <= foot_marker.location[2] and compare_x:
                    v.select = True
                    selected_index.append(v.index)
            
            bound_front = 10000.0

            # find the boundaries
            print("    Find foot boundaries...")

            clear_selection()

            # get bound back by raycast for more accurate detection
            ray_origin = Vector((foot_marker.location[0], -body_depth*10, foot_marker.location[2]))
            ray_dir = Vector((0, body_depth*100, 0))
            have_hit = True
            last_hit = ray_origin.copy()
            my_tree = BVHTree.FromBMesh(mesh)

            while have_hit:
                new_origin = last_hit+Vector((0, 0.001, 0))
                hit, normal, index, distance = my_tree.ray_cast(new_origin, ray_dir, ray_dir.magnitude)
                if hit != None:
                    last_hit = hit.copy()
                else:
                    have_hit = False

            ankle_bound_back = last_hit[1]
            
            for vi in selected_index:
                mesh.verts.ensure_lookup_table()
                vert_y = mesh.verts[vi].co[1]
               
                #front
                if vert_y < bound_front:
                    bound_front = vert_y


            print("    Find toes...")

            # Toes top
            bound_toes_top = -100000
            bound_toes_bot = 1000000                                 
            
            # find the toes height
            for vi in selected_index:
                mesh.verts.ensure_lookup_table()
                # find the toes end vertices
                vert_co = mesh.verts[vi].co
                vert_z = mesh.verts[vi].co[2]

                if tolerance_check(vert_co, bound_front, 1, body_depth / 7, True, side):
                    if vert_z > bound_toes_top:
                        bound_toes_top = vert_z
                        mesh.verts[vi].select = True
                    if vert_z < bound_toes_bot:
                        bound_toes_bot = vert_z

                        
            # raycast for foot direction

            side_fac = 1
            if side_idx == 1:
                side_fac= -1

            ray_origin = vectorize3([0, ankle_bound_back + (bound_front-ankle_bound_back) * 0.8, (bound_toes_bot + bound_toes_top) * 0.5]) + vectorize3([body_width*2*side_fac, 0.0, 0.0])
            ray_dir = vectorize3([-body_width*4*side_fac, 0, 0])
            have_hit = False
            iterate = 0

            while have_hit == False:
                hit, normal, index, distance = my_tree.ray_cast(ray_origin, ray_dir, ray_dir.magnitude)
                new_origin = vectorize3([ray_origin[0], ray_origin[1], ray_origin[2]*0.5])

                if hit != None:
                    compare_x = hit[0] < 0
                    if side_idx == 1:
                        compare_x = hit[0] > 0

                    if compare_x:
                        ray_origin = new_origin
                        if scn.arp_debug_mode:
                            print("Iterating foot ray...")

                        if iterate > 60:
                            self.error_message = 'Could not find the feet, are they on the ground?'                     
                            self.error_during_auto_detect = True
                            return
                    else:
                        have_hit = True
                        hit_front = hit
                        last_hit = hit
                else:
                    ray_origin = new_origin
                    if scn.arp_debug_mode:
                        print("Iterating foot ray...")
                    if iterate > 60:                      
                        self.error_message = "Could not find the feet, are they on the ground?"
                        self.error_during_auto_detect = True
                        return

                iterate += 1


            if scn.arp_debug_mode:
                print('    ray foot origin', ray_origin)
                print('    ray hit front', hit_front)

            while have_hit:
                have_hit = False
                hit, normal, index, distance = my_tree.ray_cast(last_hit+vectorize3([-0.001 * side_fac,0,0]), ray_dir, ray_dir.magnitude)
                
                if hit != None:

                    # left or right side only
                    compare_x = hit[0] > 0
                    if side_idx == 1:
                        compare_x = hit[0] < 0

                    if compare_x:
                        last_hit = hit
                        have_hit = True

            hit_back = last_hit

            if scn.arp_debug_mode:
                print('    ray hit back', hit_back)

            hit_center = (hit_back+hit_front)/2

            print("    Find ankle...\n")

            # Ankle
            clear_selection()
            
            ankle_depth = foot_marker.location[1]

            if not scn.arp_smart_depth:
                ray_origin = vectorize3([foot_marker.location[0], 0, foot_marker.location[2]]) + vectorize3([0, -body_width*2, 0])
                ray_dir = vectorize3([0, body_width*4, 0])
                hit_front = None
                last_hit = None
                have_hit = False

                while not have_hit:
                    hit, normal, index, distance = my_tree.ray_cast(ray_origin, ray_dir, ray_dir.magnitude)
                    if hit == None:
                        self.error_during_auto_detect = True
                        self.error_message = 'Could not find the ankle, marker out of mesh?'
                        return

                    else:
                        have_hit = True
                        hit_front = hit
                        last_hit = hit

                while have_hit:# iterate if multiple polygons layers
                    have_hit = False
                    hit, normal, index, distance = my_tree.ray_cast(last_hit+vectorize3([0, 0.001, 0]), ray_dir, ray_dir.magnitude)
                    if hit != None:
                        last_hit = hit
                        have_hit = True

                hit_back = last_hit

                if scn.arp_debug_mode:
                    print('    ray hit back', hit_back)

                ankle_depth = ((hit_back + hit_front)/2)[1]
                
            ankle_empty_loc = [foot_marker.location[0], ankle_depth, foot_marker.location[2]]
            ankle_endfoot_dist = (vectorize3([ankle_empty_loc[0], bound_front, ankle_empty_loc[2]]) - vectorize3(ankle_empty_loc)).magnitude


            if scn.arp_debug_mode:
                print("    Find bank bones...\n")

            # Bank bones
            clear_selection()
            foot_bot_selection = []
            
            for v in mesh.verts:
                if tolerance_check(v.co, bound_toes_bot, 2, body_height / 60, True, side):
                    v.select = True
                    foot_bot_selection.append(v.index)


            bpy.ops.object.mode_set(mode='OBJECT')

            foot_dir = vectorize3([hit_center[0] - ankle_empty_loc[0], hit_center[1] - ankle_empty_loc[1], 0])

            if side == '.l':
                scn.arp_foot_dir_l = foot_dir
            if side == '.r':
                scn.arp_foot_dir_r = foot_dir

            # find the bank bones in foot direction space
            #   create temp empty object for the coord space calculation
            angle_foot = (vectorize3([0,-1,0]).angle(foot_dir))
            foot_dir_space_name = "foot_dir_space"
            foot_dir_space = create_empty(foot_dir_space_name, Vector((0,0,0)))
            #bpy.ops.object.empty_add(type='PLAIN_AXES', radius = 1, location=(0,0,0), rotation=(0, 0, angle_foot*side_fac))
            foot_dir_space.rotation_euler = [0, 0, angle_foot*side_fac]
            #bpy.context.active_object.name = foot_dir_space_name
            #foot_dir_space = get_object(foot_dir_space_name)
            foot_dir_space.parent = get_object('arp_temp_detection')                                                       
            
            foot_dir_matrix = foot_dir_space.matrix_world

            set_active_object(body.name)
            
            bpy.ops.object.mode_set(mode='EDIT')
            
            mesh = bmesh.from_edit_mesh(bpy.context.active_object.data)
            
            # get heel back by raycast for more accurate detection                
            heel_bound_back = ankle_bound_back
            ray_or_x = foot_marker.location[0]
            ray_or_y = body_depth*10
            ray_or_z = bound_toes_bot
            ray_or_z += (foot_marker.location[2] - bound_toes_bot)*0.2# avoid too low rays
            ray_origin = Vector((ray_or_x, ray_or_y, ray_or_z))
            ray_dir = Vector((0, -body_depth*100, 0))       
         
            my_tree = BVHTree.FromBMesh(mesh)
       
            hit, normal, index, distance = my_tree.ray_cast(ray_origin, ray_dir, ray_dir.magnitude)
            if hit != None:
                heel_bound_back = hit[1]        

            #select vertices around the foot_loc
            
            heel_back = [0, heel_bound_back, 0]#[0,-10000.0,0]
            foot_left = [10000.0, 0, 0]

            if side_idx == 1:
                foot_left = [-10000.0, 0, 0]

            foot_right = [0, 0, 0]

            #find the boundaries in foot dir space
            clear_selection()

            for vi in foot_bot_selection:
                mesh.verts.ensure_lookup_table()
                vert_co = mesh.verts[vi].co @ foot_dir_matrix

                #back
                #if vert_co[1] > heel_back[1]:
                #    heel_back = vert_co
                #left
                if vert_co[1] < heel_back[1]:
                    compare_x = vert_co[0] < foot_left[0]
                    if side_idx == 1:
                        compare_x = vert_co[0] > foot_left[0]
                    if compare_x:
                        foot_left = vert_co

                    #right
                    compare_negx = vert_co[0] > foot_right[0]
                    if side_idx == 1:
                        compare_negx = vert_co[0] < foot_right[0]
                    if compare_negx:
                        foot_right = vert_co
            
            
            bank_right_loc = [foot_left[0], heel_back[1], bound_toes_bot]
            bank_left_loc = [foot_right[0], heel_back[1], bound_toes_bot]
            bank_mid_loc = [(foot_left[0] + foot_right[0])/2, heel_back[1], bound_toes_bot]
            
            z_world_vec = Vector((0,0,1))
            bank_right_loc = rotate_point(vectorize3(bank_right_loc), angle_foot, z_world_vec, vectorize3(ankle_empty_loc))
            bank_left_loc = rotate_point(vectorize3(bank_left_loc), angle_foot, z_world_vec, vectorize3(ankle_empty_loc))
            bank_mid_loc = rotate_point(vectorize3(bank_mid_loc), angle_foot, z_world_vec, vectorize3(ankle_empty_loc))
            
            bpy.ops.object.mode_set(mode='OBJECT')

            toes_end_loc = vectorize3(ankle_empty_loc) + (foot_dir.normalized() * ankle_endfoot_dist)
            toes_end_loc[2] = bound_toes_bot
            toes_start_loc = vectorize3(ankle_empty_loc) + (toes_end_loc-vectorize3(ankle_empty_loc))*0.7
            toes_start_loc[2] = (bound_toes_top + bound_toes_bot) * 0.5

            # create empty location
            foot_dict = {'ankle_loc':[ankle_empty_loc, "ankle_loc"], 'bank_left_loc':[bank_left_loc,"bank_left_loc"],
                    'bank_right_loc':[bank_right_loc, "bank_right_loc"],'bank_mid_loc':[bank_mid_loc,"bank_mid_loc"],
                    'toes_end':[toes_end_loc,"toes_end"],'toes_start':[toes_start_loc,"toes_start"]}

            for key, value in foot_dict.items():
                create_empty_loc(0.04, value[0], value[1]+side)
            

            bpy.ops.object.select_all(action='DESELECT')
            set_active_object(foot_dir_space_name)
            bpy.ops.object.delete(use_global=False)


        # ROOT POSITION --------------------------------------------------------------------------------------------

        print("Find root position...\n")

        #   get the loc guides
        root_marker = get_object("root_loc")
        set_active_object(body.name)
        bpy.ops.object.mode_set(mode='EDIT')
        mesh = bmesh.from_edit_mesh(bpy.context.active_object.data)

        #select vertices in the overlapping sphere

        hips_back = None
        hips_front = None
        hips_right = None
        hips_left = None

        my_tree = BVHTree.FromBMesh(mesh)

        # Find position by raycast
        print("  front-back...")
            # Front / Back
        ray_origin = vectorize3([root_marker.location[0], 0, root_marker.location[2]]) + vectorize3([0, -body_width*2, 0])
        ray_dir = vectorize3([0, body_width*4, 0])
        last_hit = None
        have_hit = False

        while not have_hit:
            hit, normal, index, distance = my_tree.ray_cast(ray_origin, ray_dir, ray_dir.magnitude)
            if hit == None:
                self.error_during_auto_detect = True
                self.error_message = 'Could not find the root pos, marker out of mesh?'
                return

            else:
                have_hit = True
                hips_front = hit
                last_hit = hit

        unit_delta = body_depth/100

        while have_hit:#iterate if multiple polygons layers
            have_hit = False
            hit, normal, index, distance = my_tree.ray_cast(last_hit+vectorize3([0, unit_delta, 0]), ray_dir, ray_dir.magnitude)
            if hit != None:
                last_hit = hit
                have_hit = True

        hips_back = last_hit


        # Surface method
        #    select vertices in the overlapping sphere
        print("  sides...")
        print("  select")
        root_selection = []
        clear_selection()
        base_dist = body_width / 15
        r_dist = base_dist
        vert_sel = []
        hips_bound_right = None
        hips_bound_left = None

        has_selected = False

        while not has_selected:
            for v in mesh.verts:
                if tolerance_check_2(v.co, root_marker.location, 0, 2, r_dist, ".l"):
                    vert_sel.append(v)
                    has_selected = True
                    if hips_bound_right == None:
                        hips_bound_right = v.co[0]
                    if v.co[0] > hips_bound_right:
                        hips_bound_right = v.co[0]
            r_dist += base_dist

        has_selected = False

        while not has_selected:
            for v in mesh.verts:
                if tolerance_check_2(v.co, root_marker.location, 0, 2, r_dist, ".r"):
                    vert_sel.append(v)
                    has_selected = True
                    if hips_bound_left == None:
                        hips_bound_left = v.co[0]
                    if v.co[0] < hips_bound_left:
                        hips_bound_left = v.co[0]

            r_dist += base_dist

        time_start = time.time()
        
        print("  get boundaries")
        found_boundary = False
        
        while not found_boundary:
            found_boundary = True
            for vidx, vert in enumerate(vert_sel):
                time_current = time.time() - time_start
              
                for edge in vert.link_edges:
                    for v in edge.verts:
                        if not v in vert_sel and v.co[0] > vert.co[0]:
                            if tolerance_check(v.co, root_marker.location[2], 2, body_width / 15, True, ".l"):
                                vert_sel.append(v)
                                found_boundary = False
                                if v.co[0] > hips_bound_right:
                                    hips_bound_right = v.co[0]
                                    
                if time_current > 10.0:
                    found_boundary = True
                    break
                    
                print_progress_bar("Verts", vidx, len(vert_sel))

        
        time_start = time.time()    
        found_boundary = False
        
        while not found_boundary:
            found_boundary = True
            for vidx, vert in enumerate(vert_sel):
                time_current = time.time() - time_start
                
                for edge in vert.link_edges:
                    for v in edge.verts:
                        if not v in vert_sel and v.co[0] < vert.co[0]:
                            if tolerance_check(v.co, root_marker.location[2], 2, body_width / 15, True, ".r"):
                                vert_sel.append(v)
                                found_boundary = False
                                if v.co[0] < hips_bound_left:
                                    hips_bound_left = v.co[0]
                                    
                if time_current > 10.0:
                    found_boundary = True
                    break
                    
                print_progress_bar("Verts", vidx, len(vert_sel))

        # Todo, skip the depth evaluation if arp_smart_depth is off
        root_depth = root_marker.location[1] if scn.arp_smart_depth else (hips_back[1]+hips_front[1])/2 
        
        hips_right = Vector((hips_bound_right, (hips_back[1]+hips_front[1])/2, root_marker.location[2]))
        hips_left = Vector((hips_bound_left, (hips_back[1]+hips_front[1])/2, root_marker.location[2]))

        if scn.arp_smart_sym:
            hips_left = Vector((-hips_bound_right, (hips_back[1]+hips_front[1])/2, root_marker.location[2]))

        root_empty_loc = [root_marker.location[0], root_depth, root_marker.location[2]]


         # Legs detection --------------------------------------------------------------------------------------------
        for side_idx, foot_marker in enumerate(foot_markers):
            if side_idx == 0:
                print('\n[Left leg detection...]')
            elif side_idx == 1:
                print('\n[Right leg detection...]')

            side = ".l"
            hips_side = hips_right
            ankle_empty_loc = get_object("ankle_loc.l_auto").location
            
            if side_idx == 1:
                hips_side = hips_left
                ankle_empty_loc = get_object("ankle_loc.r_auto").location
                side = ".r"
            
            leg_empty_loc = [(hips_side[0])/2, root_empty_loc[1], root_empty_loc[2]]
            
            # Todo: skip leg/thigh evaluation if thigh_loc is here
            thigh_loc_obj = get_object('thigh_loc') if side_idx == 0 else get_object('thigh_loc_sym')
            if thigh_loc_obj:
                leg_empty_loc[0], leg_empty_loc[2] = thigh_loc_obj.location[0], thigh_loc_obj.location[2]
                if scn.arp_smart_depth:
                    leg_empty_loc[1] = thigh_loc_obj.location[1]
            
            knee_empty_loc = [(leg_empty_loc[0] + ankle_empty_loc[0])/2, 0, (leg_empty_loc[2] + ankle_empty_loc[2])/2]
            bot_empty_loc = [leg_empty_loc[0], -hips_front[1], leg_empty_loc[2]]

            # find the knee boundaries
            if scn.arp_debug_mode:
                print("    Find knee boundaries...\n")

            set_active_object(body.name)
            bpy.ops.object.mode_set(mode='EDIT')
            mesh = bmesh.from_edit_mesh(bpy.context.active_object.data)

            clear_selection()
            knee_selection = []
            has_selected_knee = False
            sel_dist = body_height / 25

            while has_selected_knee == False:
                for vb in mesh.verts:
                    if tolerance_check(vb.co, knee_empty_loc[2], 2, sel_dist, True, side):
                        vb.select = True
                        knee_selection.append(vb.index)
                        has_selected_knee = True

                sel_dist *= 2

            knee_back = -10000
            knee_front = 10000
            knee_left = 10000
            knee_right = -10000

            for vk in knee_selection:
                mesh.verts.ensure_lookup_table() #debug_mode
                vert_y = mesh.verts[vk].co[1]
                vert_x = mesh.verts[vk].co[0]

                #front
                if vert_y < knee_front:
                    knee_front = vert_y
                # back
                if vert_y > knee_back:
                    knee_back = vert_y
                # left
                if vert_x < knee_left:
                    knee_left = vert_x
                # right
                if vert_x > knee_right:
                    knee_right = vert_x

            knee_empty_loc[0] = knee_left + (knee_right - knee_left)*0.5

            # ensure the knee Y position is inside by raycasting, more accurate
            my_tree = BVHTree.FromBMesh(mesh)
            knee_front_rayc = None
            knee_back_rayc = None

            last_hit = None
            have_hit = False
            ray_origin = vectorize3([knee_empty_loc[0], 0, knee_empty_loc[2]]) + vectorize3([0, -body_width*2, 0])
            ray_dir = vectorize3([0, body_width*4, 0])
            #   front
            hit, normal, index, distance = my_tree.ray_cast(ray_origin, ray_dir, ray_dir.magnitude)
            if hit:
                knee_front_rayc = hit[1]
                last_hit = hit
                have_hit = True

            unit_delta = body_depth/100

            #   back
            while have_hit:#iterate in case of multiple polygons layers
                have_hit = False
                hit, normal, index, distance = my_tree.ray_cast(last_hit+vectorize3([0, unit_delta, 0]), ray_dir, ray_dir.magnitude)
                if hit:
                    last_hit = hit
                    have_hit = True

            if last_hit:# if None, raycast failed, probably due to the knee being shifted on the side?
                knee_back_rayc = last_hit[1]

            if knee_front_rayc and knee_back_rayc:
                knee_empty_loc[1] = knee_back_rayc + (knee_front_rayc - knee_back_rayc)*0.75
            else:
                knee_empty_loc[1] = knee_back + (knee_front - knee_back)*0.75

            bpy.ops.object.mode_set(mode='OBJECT')
            
            # TODO: skip knee evaluation if knee_loc is here
            if get_object('knee_loc'):
                knee_loc_obj = get_object('knee_loc') if side_idx == 0 else get_object('knee_loc_sym')
                knee_empty_loc[0], knee_empty_loc[2] = knee_loc_obj.location[0], knee_loc_obj.location[2]
                
                if scn.arp_smart_depth:                   
                    knee_empty_loc[1] = knee_loc_obj.location[1]

            create_empty_loc(0.04, root_empty_loc, "root_loc")
            create_empty_loc(0.04, leg_empty_loc, "leg_loc"+side)
            create_empty_loc(0.04, knee_empty_loc, "knee_loc"+side)
            create_empty_loc(0.04, bot_empty_loc, "bot_empty_loc"+side)

    
        print("\nFind neck...\n")

        #   Neck
        neck_loc = get_object("neck_loc")
        set_active_object(body.name)
        
        bpy.ops.object.mode_set(mode='EDIT')
        
        mesh = bmesh.from_edit_mesh(bpy.context.active_object.data)
     
        clear_selection()
      
        if scn.arp_debug_mode:
            print("    Find neck boundaries...\n")

        if not scn.arp_smart_depth:
            # find the neck bounds
            ray_origin = Vector((neck_loc.location[0],-body_depth*2, neck_loc.location[2]))
            ray_dir = vectorize3([0, body_depth*4, 0])

            hit, normal, index, distance = my_tree.ray_cast(ray_origin, ray_dir, ray_dir.magnitude)
            neck_back = None
            
            if distance == None or distance < 0.001:            
                self.error_during_auto_detect = True
                self.error_message = 'Could not find the neck, marker out of mesh?'
                return
            else:
                neck_front = hit
                have_hit = True
                last_hit = hit
                #iterate if multiples faces layers
                while have_hit:
                    have_hit = False
                    hit, normal, index, distance = my_tree.ray_cast(last_hit + vectorize3([0,0.001,0]), ray_dir, ray_dir.magnitude)
                    if hit != None:
                        have_hit = True
                        last_hit = hit

                neck_back = last_hit
        
        neck_depth = None            
        if scn.arp_smart_depth:
            neck_depth = get_object('neck_loc').location[1]
        else:
            neck_depth = neck_back[1] + (neck_front[1]-neck_back[1])*0.45
            
        neck_empty_loc = [neck_loc.location[0], neck_depth, neck_loc.location[2]]


        # Spine 01
        print("Find spine 01...\n")
        
        my_tree = BVHTree.FromBMesh(mesh)
        vec =  (neck_loc.location - root_marker.location)*1/3
        ray_origin = root_marker.location + vec + vectorize3([0,-body_depth*2,0])
        ray_dir = vectorize3([0,body_depth*4,0])

        hit, normal, index, distance = my_tree.ray_cast(ray_origin, ray_dir, ray_dir.magnitude)
        i = 0
        while hit == None and i < 5000:# hole in the chest? move up origin
            ray_origin = ray_origin + vec*0.05
            hit, normal, index, distance = my_tree.ray_cast(ray_origin, ray_dir, ray_dir.magnitude)
        if distance == None or distance < 0.001:
            self.error_during_auto_detect = True
            self.error_message = 'Could not find spine 01, marker out of mesh'
            return

        else:
            spine_01_front = hit
            have_hit = True
            last_hit = hit
            #iterate if multiples faces layers
            while have_hit:
                have_hit = False
                hit, normal, index, distance = my_tree.ray_cast(last_hit+vectorize3([0,0.001,0]), ray_dir, ray_dir.magnitude)
                if hit != None:
                    have_hit = True
                    last_hit = hit

            spine_01_back = last_hit

        spine_01_empty_loc = spine_01_front + (spine_01_back-spine_01_front)*0.65
        if scn.arp_smart_depth:
            spine_01_empty_loc[1] = root_depth


        # Spine 02
        vec =  (neck_loc.location - root_marker.location)*2/3
        ray_origin = root_marker.location + vec + vectorize3([0,-body_depth*2,0])
        ray_dir = vectorize3([0,body_depth*4,0])

        hit, normal, index, distance = my_tree.ray_cast(ray_origin, ray_dir, ray_dir.magnitude)
        i = 0
        while hit == None and i < 5000:# hole in the chest? move up origin
            ray_origin = ray_origin + vec*0.05
            hit, normal, index, distance = my_tree.ray_cast(ray_origin, ray_dir, ray_dir.magnitude)
        if hit == None or distance < 0.001:
            self.error_during_auto_detect = True
            self.error_message = 'Could not find spine 02, marker out of mesh'
            return        
        else:
            spine_02_front = hit
            have_hit = True
            last_hit = hit
            #iterate if multiples faces layers
            while have_hit:
                have_hit = False
                hit, normal, index, distance = my_tree.ray_cast(last_hit+vectorize3([0,0.001,0]), ray_dir, ray_dir.magnitude)
                if hit != None:
                    have_hit = True
                    last_hit = hit

            spine_02_back = last_hit

        spine_02_empty_loc = spine_02_front + (spine_02_back-spine_02_front)*0.65
        if scn.arp_smart_depth:
            spine_02_empty_loc[1] = root_depth
        
        # Breast
        print("Find breast...\n")

        #select vertices near spine02
        spine_02_selection = []
        clear_selection()
        has_selected_spine_02 = False
        sel_dist = body_height / 17

        while has_selected_spine_02 == False:
            for vb in mesh.verts:
                if tolerance_check_2(vb.co, spine_02_empty_loc, 0, 2, sel_dist, ".l"):
                    vb.select = True
                    spine_02_selection.append(vb.index)
                    has_selected_spine_02 = True

            sel_dist *= 2


        # find the spine 02 front bound
        spine_02_back = -1000
        spine_02_front = 1000

        if scn.arp_debug_mode:
            print("    Find breast boundaries...\n")

        for vs in spine_02_selection:
            mesh.verts.ensure_lookup_table()
            vert_y = mesh.verts[vs].co[1]
            #front
            if vert_y < spine_02_front:
                spine_02_front = vert_y
             #back
            if vert_y > spine_02_back:
                spine_02_back = vert_y


        breast_01_loc = [shoulder_pos[0]/2, spine_02_front, spine_02_empty_loc[2]]
        breast_02_loc = [shoulder_pos[0]/2, breast_01_loc[1] + (shoulder_pos[1]-breast_01_loc[1])*0.4, spine_02_empty_loc[2]+ (shoulder_pos[2]-spine_02_empty_loc[2])*0.5]

    
    # Head
    xpos = 0
    head_height = None
    chin_loc = get_object("chin_loc")

    if chin_loc == None:# backward-compatibility, chin was not defined in earlier versions  
        head_height = neck_empty_loc[2] + (body_height - neck_empty_loc[2])*0.25
    else:
        if scn.arp_smart_type == 'BODY':
            head_height = chin_loc.location[2] + (chin_loc.location[2] - neck_loc.location[2])*0.2
        elif scn.arp_smart_type == 'FACIAL':
            head_height = chin_loc.location[2]
            
        xpos = chin_loc.location[0]

    
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    set_active_object(body.name)   
    bpy.ops.object.mode_set(mode='EDIT')
            
    mesh = bmesh.from_edit_mesh(bpy.context.active_object.data)
    my_tree = BVHTree.FromBMesh(mesh)
    
    # raycast the chin
    ray_origin = chin_loc.location + Vector((0.0, -body_depth*2, 0.0))
    ray_dir = vectorize3([0.0, body_depth*4, 0.0])    
    
    hit, normal, index, distance = my_tree.ray_cast(ray_origin, ray_dir, ray_dir.magnitude)
    if hit == None:
        print('    Could not find head pos, marker out of mesh?')
    else:
        chin_loc.location = hit + Vector((0.0, -body_depth*0.01, 0.0))    
    
    # head
    head_tip_loc = get_object('head_tip_loc')
    head_empty_loc = None
    
    if head_tip_loc and scn.arp_smart_depth:# head tip defined, use it
        head_empty_loc = [head_tip_loc.location[0], head_tip_loc.location[1], chin_loc.location[2] + (head_tip_loc.location[2]-chin_loc.location[2])*0.15]
        
    else:# head tip marker not there, raycast the head joint
        ray_origin = Vector((xpos, -body_depth*2, head_height))
        ray_dir = vectorize3([0.0, body_depth*4, 0.0])    
        
        hit, normal, index, distance = my_tree.ray_cast(ray_origin, ray_dir, ray_dir.magnitude)

        if distance == None or distance < 0.001:
            print('    Could not find head pos, marker out of mesh?')
        else:
            head_front = hit
            
            have_hit = True
            last_hit = hit
            #iterate if multiples faces layers
            while have_hit:
                have_hit = False
                hit, normal, index, distance = my_tree.ray_cast(last_hit+vectorize3([0,0.001,0]), ray_dir, ray_dir.magnitude)
                if hit != None:
                    have_hit = True
                    last_hit = hit

            head_back = last_hit
    
        mid_head_y = (head_front[1] + head_back[1]) * 0.5
        head_loc_y = head_back[1] + (head_front[1] - head_back[1]) * 0.3 if scn.arp_smart_type == 'FACIAL' else (mid_head_y + neck_empty_loc[1])*0.5
        head_empty_loc = [chin_loc.location[0], head_loc_y, head_height]
        
        
    # head end
    head_end_empty_loc = None
    
    if head_tip_loc:# head tip defined, use it
        if scn.arp_smart_depth:
            head_end_empty_loc = head_tip_loc.location.copy()
        else:
            head_end_empty_loc = [head_tip_loc.location[0], head_empty_loc[1], head_tip_loc.location[2]]
        
    else:# get the head top by raycast    
        ray_dir = Vector((0, body_depth*4, 0))
        body_top = None
        head_top = None
        
        if scn.arp_smart_type == 'FACIAL':# 'facial only' mode has no toes markers
            body_top = body.bound_box[1][2]
        else:
            body_top = body_height + get_object('toes_end.l_auto').location[2]# add offset if feet above ground
            
        ray_ori = Vector((chin_loc.location[0], -body_depth*2, body_top))
        ray_offset = (body_top - head_height)/100
        have_hit = False
        ray_count = 0

        while not have_hit and ray_count < 400:
            ray_count += 1
            hit1, normal, index, distance = my_tree.ray_cast(ray_ori - Vector((0, 0, ray_offset))*ray_count, ray_dir, ray_dir.magnitude )

            if hit1 != None:
                have_hit = True
                
        if have_hit:
            if hit1[2] >= head_height:
                head_top = hit1
                print("Found head top by raycast")
            else:
                print("Head top by raycast is below the neck, disabling raycast")
                head_top = Vector((0, 0, body_top))
                print("")
        else:
            print("Raycast failed, head top is the body height")
            head_top = Vector((chin_loc.location[0], 0, body_top))

        head_end_empty_loc = [chin_loc.location[0], head_empty_loc[1], head_top[2]]

    # create the empties
    bpy.ops.object.mode_set(mode='OBJECT')
    
    if scn.arp_smart_type == 'BODY':
        create_empty_loc(0.04, neck_empty_loc, "neck_loc")
        create_empty_loc(0.04, spine_01_empty_loc, "spine_01_loc")
        create_empty_loc(0.04, spine_02_empty_loc, "spine_02_loc")
        create_empty_loc(0.04, breast_01_loc, "breast_01_loc")
        create_empty_loc(0.04, breast_02_loc, "breast_02_loc")
        
    create_empty_loc(0.04, head_end_empty_loc, "head_end_loc")
    create_empty_loc(0.04, head_empty_loc, "head_loc")
    

    # restore pivot mode    
    scn.tool_settings.transform_pivot_point = pivot_mod

    # update hack
    bpy.ops.transform.translate(value=(0, 0, 0))

    if scn.arp_debug_mode:
        print("End Auto-Detection.\n")


#-- end _auto_detect()


def _delete_detected():
    clear_object_selection()
    if get_object('auto_detect_loc') != None:
        get_object("auto_detect_loc").select_set(state=1)
        bpy.context.view_layer.objects.active = get_object("auto_detect_loc")

        bpy.ops.object.select_grouped(type='CHILDREN_RECURSIVE')
        bpy.ops.object.delete()
        get_object("auto_detect_loc").select_set(state=1)

        bpy.ops.object.delete()


def _cancel_and_delete_markers():
    scene = bpy.context.scene

    # Save all markers position for later restore
        # Clear it first
        # Clear the bone collection
    if len(scene.arp_markers_save):
        i = len(scene.arp_markers_save)
        while i >= 0:
            scene.arp_markers_save.remove(i)
            i -= 1

    if len(scene.arp_facial_markers_save):
        i = len(scene.arp_facial_markers_save)
        while i >= 0:
            scene.arp_facial_markers_save.remove(i)
            i -= 1

    # Store in property
    arp_markers = get_object("arp_markers", view_layer_change=True)
    for obj in arp_markers.children:
        item = scene.arp_markers_save.add()
        item.name = obj.name
        item.location = obj.location
        if bpy.context.scene.arp_debug_mode:
            print("Saving marker:", item.name)

    # Add the mirror state
    item = scene.arp_markers_save.add()
    item.name = "mirror_state"
    ms = 1
    if not scene.arp_smart_sym:
        ms = 0
    item.location = [ms, ms, ms]
    
    # Add facial options states
    item = scene.arp_markers_save.add()
    item.name = "ears_state"
    val = 1 if scene.arp_smart_ears else 0
    item.location = [val, val, val]
    
    item = scene.arp_markers_save.add()
    item.name = "eyebrows_state"
    val = 1 if scene.arp_smart_eyebrows else 0
    item.location = [val, val, val]
    
    item = scene.arp_markers_save.add()
    item.name = 'nose_state'
    val = 1 if scene.arp_smart_nose else 0
    item.location = [val, val, val]
    
    item = scene.arp_markers_save.add()
    item.name = 'cheek_state'
    val = 1 if scene.arp_smart_cheeks else 0
    item.location = [val, val, val]
    
    item = scene.arp_markers_save.add()
    item.name = 'eyes_state'
    val = 1 if scene.arp_smart_eyes else 0
    item.location = [val, val, val]
    
    item = scene.arp_markers_save.add()
    item.name = 'mouth_state'
    val = 1 if scene.arp_smart_mouth else 0
    item.location = [val, val, val]
    
    item = scene.arp_markers_save.add()
    item.name = 'teeth_state'
    val = 1 if scene.arp_smart_teeth else 0
    item.location = [val, val, val]
    
    item = scene.arp_markers_save.add()
    item.name = 'tongue_state'
    val = 1 if scene.arp_smart_tongue else 0
    item.location = [val, val, val]
    
    item = scene.arp_markers_save.add()
    item.name = 'chin_state'
    val = 1 if scene.arp_smart_chin else 0
    item.location = [val, val, val]

    # facial markers
    arp_facial_setup = get_object("arp_facial_setup", view_layer_change=True)
    if arp_facial_setup:
        for vert in arp_facial_setup.data.vertices:
            item = scene.arp_facial_markers_save.add()
            item.id = vert.index
            item.location = arp_facial_setup.matrix_world @ vert.co

    clear_object_selection()

    #arp_markers.select_set(state=1)

    delete_children(arp_markers, "OBJECT")    

    body_tmp = get_object("body_temp", view_layer_change=True)
    if body_tmp:
        delete_object(body_tmp)

    if arp_facial_setup:
        delete_object(arp_facial_setup)
    #bpy.ops.object.delete()
    
    
def set_selection_filters(types, state):
    current_area = bpy.context.area
    space_view3d = [i for i in current_area.spaces if i.type == "VIEW_3D"]

    for v in space_view3d:
        for t in types:
            if t == 'EMPTY':
                v.show_object_select_empty = state
                v.show_object_viewport_empty = state
            elif t == 'ARMATURE':
                v.show_object_select_armature = state
                v.show_object_viewport_armature = state
            elif t == 'MESH':
                v.show_object_select_mesh = state
                v.show_object_viewport_mesh = state
                
                
def show_extras(state):
    current_area = bpy.context.area
    space_view3d = [i for i in current_area.spaces if i.type == "VIEW_3D"]

    for v in space_view3d:
        v.overlay.show_extras = state
        # disable normals display, cluttering...
        v.overlay.show_vertex_normals = v.overlay.show_split_normals = v.overlay.show_face_normals = False


def _get_selected_objects():
    scn = bpy.context.scene
    scn.arp_body_name = bpy.context.view_layer.objects.active.name

    try:
        bpy.context.space_data.overlay.show_relationship_lines= False
    except:
        pass

    bpy.ops.object.mode_set(mode='OBJECT')
    
    set_selection_filters(['EMPTY', 'MESH', 'ARMATURE'], True)
    show_extras(True)
    # comment out for now. Some users like to use Gizmos to translate markers
    #bpy.context.space_data.show_gizmo = False

    
    #get character mesh name
    body = get_object(scn.arp_body_name)

    bpy.ops.object.select_all(action='DESELECT')
    set_active_object(body.name)
    bpy.context.view_layer.objects.active = body
    
    #remove parent if any
    #body.parent = None
    bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')

    # Apply transforms
    #   apply additive deltas if any
    if body.delta_location != [0.0,0.0,0.0] or body.delta_rotation_euler != [0.0,0.0,0.0] or body.delta_scale != [1.0,1.0,1.0]:        
        body.location += body.delta_location.copy()        
        for i, j in enumerate(body.rotation_euler):
            body.rotation_euler[i] += body.delta_rotation_euler[i]       
        body.scale += (body.delta_scale.copy() - Vector((1,1,1)))
        
        # zero out
        body.delta_location = body.delta_rotation_euler = [0,0,0]
        body.delta_scale = [1,1,1]
        
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    bpy.ops.object.mode_set(mode='EDIT')

    # set to vertex selection mode
    bpy.ops.mesh.select_mode(type="VERT")

    # remove double
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=1e-006)
    bpy.ops.object.mode_set(mode='OBJECT')

    # remove any armature modifier
    if len(body.modifiers):
        for modifier in body.modifiers:
            if modifier.type == 'ARMATURE':
                bpy.ops.object.modifier_remove(modifier=modifier.name)

    # make sure the mesh is displayed in a correct grey solid color
    body.color = [1.0, 1.0 , 1.0, 1.0]
    
    #center front view
    bpy.ops.view3d.view_axis(type='FRONT')
    bpy.ops.view3d.view_selected(use_all_regions=False)
    

    # make sure the selected objects collections are not hidden
    for col in body.users_collection:
        vl = bpy.context.view_layer.layer_collection
        col.hide_viewport = False
        if col.name != "Master Collection":
            try:
                vl.children[col.name].hide_viewport = False
            except:# the collection is not a children of the current view layer
                pass

    # make sure the active collection is not hidden, otherwise we can't access the newly created object data
    active_collec = bpy.context.layer_collection
    if not active_collec.is_visible:
        vl = bpy.context.view_layer.layer_collection
        if active_collec.hide_viewport:
            active_collec.hide_viewport = False
        if active_collec.name != "Master Collection":
            vl_active_col = vl.children.get(active_collec.name)
            if vl_active_col:
                if vl_active_col.hide_viewport:# direct hidden state
                    vl_active_col.hide_viewport = False
        """
        for col in body.users_collection:

            layer_col = auto_rig.search_layer_collection(bpy.context.view_layer.layer_collection, col.name)
            if layer_col.hide_viewport == False and col.hide_viewport == False:
                bpy.context.view_layer.active_layer_collection = layer_col
                break
        """


    # add the arp_markers empty object
    create_arp_markers()    
    
    bpy.ops.object.select_all(action='DESELECT')

    # set ortho
    bpy.context.space_data.region_3d.view_perspective = 'ORTHO'

    # freeze character selection
    get_object(scn.arp_body_name).hide_select = True
    
    rig = get_object('rig')
    if rig:
        rig.hide_select = True
        rig["arp_smart_selection_hidden"] = True                                        
        hide_object(rig)
        
    # check if AI is installed
    inf_path = get_AI_path()
    scn.arp_smart_AI_is_installed = os.path.exists(inf_path)
    
    scn.arp_smart_fingers_engine = 'AI' if scn.arp_smart_AI_is_installed else 'LEGACY'


def remove_fingers_markers():
    for _s in ['_sym', '']:
        for fname in ['thumb', 'index', 'middle', 'ring', 'pinky']:
            for i in range(1, 5):
                marker_obj = get_object(fname+str(i)+'_loc'+_s)
                if marker_obj:
                    # static debug icons if any
                    children = [c.name for c in marker_obj.children]
                    for childname in children:
                        delete_object(get_object(childname))
                    delete_object(marker_obj)
                    
    if get_object('hand_loc'):
        set_active_object('hand_loc')
    
    
def update_fingers_to_detect(self, context):
    if context.scene.arp_fingers_to_detect < 4:# AI fingers only for 4-5 fingers for now
        context.scene.arp_smart_fingers_engine = 'LEGACY'
        remove_fingers_markers()
        

def update_fingers_enable(self, context):
    if context.scene.arp_fingers_enable == False:
        remove_fingers_markers()
        

def update_fingers_engine(self, context):
    if context.scene.arp_smart_fingers_engine == 'LEGACY':
        remove_fingers_markers()
    
    
def update_sym(self, context):
    mid_markers =  ['chin', 'head_tip', 'neck', 'root']
    
    # Mirror the markers or not
    if get_object("arp_markers") != None:
        if len(get_object("arp_markers").children) > 0:
            for child in get_object("arp_markers").children:
                # symmetrical markers
                if "_sym" in child.name:
                    if len(child.constraints) > 0:
                        # lock mirror
                        if context.scene.arp_smart_sym:
                            child.constraints[0].influence = 1.0

                        # unlock mirror
                        else:
                            final_mat = child.matrix_world
                            child.constraints[0].influence = 0.0
                            child.matrix_world = final_mat
                # center markers
                if any(n in child.name for n in mid_markers):
                    # lock x-axis
                    if context.scene.arp_smart_sym:
                        child.lock_location[0] = True
                        child.location[0] = 0.0

                    # unlock x-axis
                    else:
                        child.lock_location[0] = False

    # set facial X Mirror
    facial_setup_obj = get_object("arp_facial_setup")
    if facial_setup_obj:
        facial_setup_obj.data.use_mirror_x = context.scene.arp_smart_sym

        if context.scene.arp_smart_sym:
            # must be in object mode to set vertices coordinates
            active_obj = bpy.context.active_object
            curr_mod = None
            if active_obj == facial_setup_obj:
                curr_mod = bpy.context.mode
                bpy.ops.object.mode_set(mode='OBJECT')
            # mirror facial vertices from left to right
            facial_markers = ard.facial_markers
            for bname in facial_markers:
                if bname.endswith(".r"):
                    left_bname = bname[:-2] + ".l"
                    left_vert_idx = facial_markers[left_bname]
                    left_vert = facial_setup_obj.data.vertices[left_vert_idx]
                    right_vert_idx = facial_markers[bname]
                    right_vert = facial_setup_obj.data.vertices[right_vert_idx]
                    right_vert.co = Vector((-left_vert.co[0], left_vert.co[1], left_vert.co[2]))

            if curr_mod:# restore mode
                restore_current_mode(curr_mod)


# COLLECTION PROPERTIES DEFINITION
class bone_transform(bpy.types.PropertyGroup):
    name : StringProperty(name="Bone name", default="")
    head : FloatVectorProperty(name="Head Position", default=(0.0, 0.0, 0.0), subtype='TRANSLATION', size=3)
    tail : FloatVectorProperty(name="Tail Position", default=(0.0, 0.0, 0.0), subtype='TRANSLATION', size=3)
    roll : FloatProperty(name="Head Position", default=0.0)


class markers_transform(bpy.types.PropertyGroup):
    location : FloatVectorProperty(name="Position", default=(0.0,0.0,0.0), subtype='TRANSLATION', size=3)


class facial_markers_transform(bpy.types.PropertyGroup):
    location : FloatVectorProperty(name="Position", default=(0.0,0.0,0.0), subtype='TRANSLATION', size=3)
    id : IntProperty(name="Vertex Id")

# END FUNCTIONS

###########  UI PANEL  ###################

def get_custom_icon(name):
    # a user reported an error when loading custom icons on Mac, if multiple Blender versions are installed
    # due to a disk read permission issue
    # then return a null id -1 if custom_icons is None
    return custom_icons[name].icon_id if custom_icons else -1

class ARP_PT_proxy_utils_ui(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ARP"
    bl_label = "Auto-Rig Pro: Smart"
    bl_idname = "ARP_PT_auto_rig_detect"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    # panel visibility conditions
    def poll(cls, context):
        if context.mode == 'POSE' or context.mode == 'OBJECT' or context.mode == 'EDIT_ARMATURE' or context.mode == 'EDIT_MESH':
            return True
        else:
            return False

    #draw
    def draw(self, context):
        global custom_icons
        layout = self.layout
        scn = context.scene
        
        # help button
        if get_prefs().beginner_mode:
            row = layout.column().row(align=True).split(factor=0.9)        
            row.label(text="")
            but = row.operator("arp.open_link_internet", text='', icon_value=get_custom_icon('question'))
            but.link_string = ard.doc_url+"auto_rig.html#smart"
        
            
        button_state = 0
        button_opt_state = 0

        #BUTTONS
        arp_facial_is_there = True if get_object('arp_facial_setup') else False
        
        if get_object("arp_markers"):
            button_state = 1
            
            if scn.arp_smart_type == 'BODY':
                if get_object("neck_loc"):
                    button_state = 2
                if get_object("chin_loc"):
                    button_state = 3
                if get_object("shoulder_loc"):
                    button_state = 4
                if get_object("hand_loc"):
                    button_state = 5
                    if scn.arp_smart_depth == False:# skip hand tip if depth is disabled
                        button_state = 6
                if get_object("hand_tip_loc"):
                    button_state = 6
                if get_object("root_loc"):
                    button_state = 7
                if get_object("foot_loc"):
                    button_state = 8
                
                #if get_object('thigh_loc'):
                #    button_opt_state = 1
                #if get_object('knee_loc'):
                #    button_opt_state = 2
                #if get_object('elbow_loc'):
                #    button_opt_state = 3

            elif scn.arp_smart_type == 'FACIAL':
                if get_object("chin_loc"):
                    button_state = 8                
            if arp_facial_is_there:
                if is_object_hidden(get_object('arp_facial_setup')) == False:
                    button_state = 9


        if button_state == 0:
            if platform.system() == "Darwin":
                col = layout.column(align=True)
                col.label(text="Mac Detected", icon='ERROR')
                row = col.row(align=True)
                row.label(text="If Mac freezes or crashes, click this:")
                #row.label(text="Disable FX to avoid crashes:")
                row.prop(scn, 'arp_disable_smart_fx', text='')
                but = col.operator("arp.open_link_internet", text='Learn More', icon='INTERNET' if bpy.app.version >= (4,2,0) else 'WORLD')
                but.link_string = ard.doc_url+"auto_rig.html#mac-warning"
                col.separator()
            
            if scn.arp_disable_smart_fx:
                col = layout.column(align=True)
                col.label(text='FX disabled. GPU icons will')
                col.label(text='be replaced by static icons (safe)')
                col.separator()
            
            layout.operator("id.get_selected_objects", text="Get Selected Objects")
            
        if button_state == 1:
            col = layout.column(align=True)
            split=col.split(align=True)
            #row.alignment = 'LEFT'
            split.label(text="Turn:")
            btn = split.operator("id.turn", text='', icon_value=get_custom_icon('rotate'))
            btn.action = "negative"
            btn = split.operator("id.turn", text='', icon_value=get_custom_icon('rotate_inv'))
            btn.action = "positive"
            
            if scn.arp_smart_type == 'BODY':
                if scn.arp_smart_AI_is_installed:
                    layout.prop(scn, 'arp_smart_sym', text='Symmetrical Character')
                    if scn.arp_smart_sym:
                        col = layout.column(align=True)                        
                        col.prop(scn, 'arp_smart_AI_body_samples', text='Samples', slider=True)
                        col = col.column(align=True)
                        col.operator('arp.guess_markers', text='Guess Markers!', icon_value=get_custom_icon('sparkles'))
                        col.scale_y = 1.3
                        
                #layout.template_icon(icon_value=pcoll['marker_neck_help'].icon_id, scale=3.0)
                props = layout.operator("id.add_marker", text="Add Neck", icon='PLUS')
                props.body_part = "neck"
            elif scn.arp_smart_type == 'FACIAL':
                layout.template_icon(icon_value=pcoll['marker_chin_help'].icon_id, scale=3.0)
                props = layout.operator("id.add_marker", text="Add Chin", icon='PLUS')
                props.body_part = "chin"
                
        if button_state > 1:
            marker_selected = False
            if bpy.context.active_object.name == 'neck_loc':
                layout.template_icon(icon_value=pcoll['marker_neck_help'].icon_id, scale=3.0)
                marker_selected = True
            elif bpy.context.active_object.name.startswith('chin_loc'):
                layout.template_icon(icon_value=pcoll['marker_chin_help'].icon_id, scale=3.0)
                marker_selected = True
            elif bpy.context.active_object.name.startswith('shoulder_loc'):
                layout.template_icon(icon_value=pcoll['marker_shoulder_help'].icon_id, scale=3.0)
                marker_selected = True
            elif bpy.context.active_object.name.startswith('hand_loc'):
                layout.template_icon(icon_value=pcoll['marker_wrist_help'].icon_id, scale=3.0)
                marker_selected = True                
            elif bpy.context.active_object.name.startswith('hand_tip_loc'):
                layout.template_icon(icon_value=pcoll['marker_handtip_help'].icon_id, scale=3.0)
                marker_selected = True
            elif bpy.context.active_object.name.startswith('root_loc'):
                layout.template_icon(icon_value=pcoll['marker_root_help'].icon_id, scale=3.0)
                marker_selected = True
            elif bpy.context.active_object.name.startswith('foot_loc'):
                layout.template_icon(icon_value=pcoll['marker_ankles_help'].icon_id, scale=3.0)
                marker_selected = True
            elif bpy.context.active_object.name.startswith('thigh_loc'):
                layout.template_icon(icon_value=pcoll['marker_thigh_help'].icon_id, scale=3.0)
                marker_selected = True
            elif bpy.context.active_object.name.startswith('knee_loc'):
                layout.template_icon(icon_value=pcoll['marker_knee_help'].icon_id, scale=3.0)
                marker_selected = True
            elif bpy.context.active_object.name.startswith('elbow_loc'):
                layout.template_icon(icon_value=pcoll['marker_elbow_help'].icon_id, scale=3.0)
                marker_selected = True
            elif bpy.context.active_object.name.startswith('head_tip'):
                layout.template_icon(icon_value=pcoll['marker_head_tip_help'].icon_id, scale=3.0)
                marker_selected = True
                
            if marker_selected:
                layout.label(text='Selected Marker: '+bpy.context.active_object.name.replace('_loc', '').replace('_sym', '').title())
            
        
        if button_state == 2:
            
            props = layout.operator("id.add_marker", text="Add Chin", icon='PLUS')
            props.body_part = "chin"
        if button_state == 3:
            props = layout.operator("id.add_marker", text="Add Shoulders", icon='PLUS')
            props.body_part = "shoulder"
        if button_state == 4:
            props = layout.operator("id.add_marker", text="Add Wrists", icon='PLUS')
            props.body_part = "hand"
        if button_state == 5:
            props = layout.operator("id.add_marker", text="Add Hand Tip", icon='PLUS')
            props.body_part = "hand_tip"
        if button_state == 6:            
            props = layout.operator("id.add_marker", text="Add Spine Root", icon='PLUS')
            props.body_part = "root"
        if button_state == 7:            
            props = layout.operator("id.add_marker", text="Add Ankles", icon='PLUS')
            props.body_part = "foot"


        if button_state >= 8 and button_state < 9:
            col = layout.column(align=True)
            
            if scn.arp_smart_type == 'BODY':    
                # optional markers
                col.menu('ARP_MT_optional_markers_menu', icon='PLUS', text='Add Optional Markers')            
                col.separator()
                col.label(text='Skeleton Settings Presets:')
                col.prop(scn, 'arp_smart_preset_settings', text='')
                
                def show_fingers_ui(panel):
                    if panel:
                        col = panel.column(align=True)
                    else:
                        col = layout.column(align=True)
                        col.prop(scn, "arp_fingers_enable", text="Fingers")
                    
                    col.enabled = scn.arp_fingers_enable
                    col_icon = col.column()                         
                    col_icon.template_icon(icon_value=pcoll['fingers'+str(scn.arp_fingers_to_detect)].icon_id, scale=2.0)
                    col.prop(scn, 'arp_fingers_to_detect', text='')                    
                    
                    if scn.arp_smart_AI_is_installed and scn.arp_fingers_to_detect >= 4 and scn.arp_smart_depth:# hand tip marker depth is required for AI fingers
                        row = col.row(align=True)
                        row.prop(scn, 'arp_smart_fingers_engine', expand=True)
                        if scn.arp_smart_fingers_engine == 'AI': 
                            col.prop(scn, 'arp_smart_AI_samples', text='Samples', slider=True)
                            col.prop(scn, 'arp_smart_AI_thresh', text='Error Threshold', slider=True)
                            col = col.column(align=True)
                            col.operator('arp.guess_fingers', text='Guess Fingers!', icon_value=get_custom_icon('sparkles'))        
                            col.scale_y = 1.3
                            
                    if scn.arp_smart_fingers_engine == 'LEGACY' or not scn.arp_smart_AI_is_installed or scn.arp_fingers_to_detect < 4 or not scn.arp_smart_depth:
                        col.prop(scn, "arp_smart_remesh_type", text="")
                        col.prop(scn, "arp_smart_remesh", slider=True)
                        col.prop(scn, "arp_finger_thickness", slider=True)
                        
                    col.separator()
                    
                # easy UI collapsable panels in Blender 4.1+
                if bpy.app.version >= (4,1,0):
                    header_fingers, panel_fingers = layout.panel('arp_smart_ui_fingers', default_closed=False)
                    header_fingers.prop(scn, 'arp_fingers_enable', text='Fingers')
                    if panel_fingers:# None if collapsed
                        show_fingers_ui(panel_fingers)
                else:
                    show_fingers_ui(None)
                    
                
                def show_spine_ui(panel):
                    if panel:
                        col = panel.column()
                    else:
                        col = layout.column(align=True)
                    col.prop(scn, 'arp_smart_spine_count', text='Spine Count')
                    row = col.row(align=True).split(factor=0.4)
                    row.label(text='Spine Shape:')
                    row.prop(scn, 'arp_smart_spine_shape', text='')
                    col.prop(scn, 'arp_smart_root_vertical', text='Pelvis Up')
                
                if bpy.app.version >= (4,1,0):
                    header_spine, panel_spine = layout.panel('arp_smart_ui_spine', default_closed=False)
                    header_spine.label(text='Spine')
                    if panel_spine:# None if collapsed
                        show_spine_ui(panel_spine)           
                else:
                    show_spine_ui(None)
                    col.separator()
                
                def show_others_ui(panel):
                    if panel:
                        col = panel.column()
                    else:
                        col = layout.column()
                    row = col.row(align=True).split(factor=0.4)
                    row.label(text='Clavicles:')
                    row.prop(scn, 'arp_smart_shoulders_align', text='')
                    col.separator()
                    col.prop(scn, "arp_smart_neck_count", text="Neck Count")
                    col.prop(scn, "arp_smart_twist_count", text="Arms-Legs Twist Count")    
                    col.separator()
                
                if bpy.app.version >= (4,1,0):
                    header_others, panel_others = layout.panel("arp_smart_ui_others", default_closed=False)
                    header_others.label(text="Others")
                    if panel_others:
                        show_others_ui(panel_others)           
                else:
                    show_others_ui(None)
                    
            col = layout.column()
            col.separator()
            col.operator('id.facial_setup', text='Add Facial' if not arp_facial_is_there else 'Edit Facial...', icon_value=get_custom_icon('mask'))

            col.separator()
            
            col = layout.column()
            col.prop(scn, 'arp_smart_overwrite')
            col = layout.column()
            col.scale_y = 1.3
            col.operator("id.go_detect", text='Go!', icon_value=get_custom_icon('sparkles'))
            col.separator()

        if button_state == 9:
            if scn.arp_smart_AI_is_installed:
                col = layout.column(align=True)
                col = col.column(align=True)
                col.prop(scn, 'arp_smart_AI_facial_samples', text='Samples', slider=True)
                col1 = col.column(align=True)
                col1.operator('arp.guess_facial', text='Guess Facial!', icon_value=get_custom_icon('sparkles'))
                col1.scale_y = 1.3            
            
            col = layout.column()
            col.prop(scn, "arp_smart_sym")
            
            col = layout.column()
            col.prop(scn, 'arp_smart_ears', text='Ears')
            col.prop(scn, 'arp_smart_eyebrows', text='Eyebrows')
            
            col.prop(scn, 'arp_smart_eyes', text='Eyes')
            if scn.arp_smart_eyes:
                col = layout.column(align=True)
                col.label(text='Eyeball Object:')
                row = col.row(align=True)
                row.prop(scn, 'arp_eyeball_type', expand=True)
                row = col.row(align=True)
                row.prop(scn, 'arp_smart_eye_shape', expand=True)
                if scn.arp_eyeball_type == 'SEPARATE':
                    col.label(text='Left Eyeball:')
                row = col.row(align=True)
                row.prop_search(scn, 'arp_eyeball_name', bpy.data, 'objects', text='')
                op = row.operator('id.smart_pick_object', text='', icon='EYEDROPPER')
                op.op_prop = 'eyeball'
                if scn.arp_eyeball_type == 'SEPARATE':
                    col.label(text='Right Eyeball:')
                    row = col.row(align=True)
                    row.prop_search(scn, 'arp_eyeball_name_right', bpy.data, 'objects', text='')
                    op = row.operator('id.smart_pick_object', text='', icon='EYEDROPPER')
                    op.op_prop = 'eyeball_right'
                    
                col.separator()
                
            col.prop(scn, 'arp_smart_nose', text='Nose')
            col.prop(scn, 'arp_smart_cheeks', text='Cheeks')
            
            col.prop(scn, 'arp_smart_mouth', text='Mouth')
            if scn.arp_smart_mouth:
                col.prop(scn, 'arp_smart_tongue', text='Tongue')
                if scn.arp_smart_tongue:
                    col.label(text="Tongue Object (optional):")
                    row = col.row(align=True)
                    row.prop_search(scn, 'arp_tongue_name', bpy.data, "objects", text="")
                    op = row.operator("id.smart_pick_object", text="", icon='EYEDROPPER')
                    op.op_prop = "tongue"
                    col.separator()
                
                col.prop(scn, 'arp_smart_teeth', text='Teeth')
                if scn.arp_smart_teeth:
                    col.label(text="Teeth Object (optional):")
                    row = col.row(align=True)
                    row.prop(scn, 'arp_teeth_type', expand=True)
                    if scn.arp_teeth_type == "SEPARATE":
                        col.label(text="Upper Teeth:")
                        
                    row = col.row(align=True)
                    row.prop_search(scn, 'arp_teeth_name', bpy.data, "objects", text="")
                    op = row.operator("id.smart_pick_object", text="", icon='EYEDROPPER')
                    op.op_prop = 'teeth'
                    
                    if scn.arp_teeth_type == "SEPARATE":
                        col.label(text="Lower Teeth:")
                        row = col.row(align=True)
                        row.prop_search(scn, "arp_teeth_lower_name", bpy.data, "objects", text="")
                        op = row.operator("id.smart_pick_object", text="", icon='EYEDROPPER')
                        op.op_prop = "teeth_lower"
            
            
            col.prop(scn, 'arp_smart_chin', text='Chin')
            col.separator()
            
            row = col.row(align=True)
            row.operator("id.cancel_facial_setup", text="Cancel Facial")
            row.operator('id.validate_facial_setup', text='OK')
                
                
        if button_state > 0 and button_state < 9:
            if button_state > 1:
                layout.prop(scn, "arp_smart_sym")
            layout.prop(scn, 'arp_smart_depth')
            col = layout.column(align=True)
            col.operator("id.restore_markers", text="Restore Last Session", icon='RECOVER_LAST')
            col.operator("id.cancel_and_delete_markers", text="Cancel and Delete Markers", icon='PANEL_CLOSE')

        layout.separator()



@persistent
def cleanup(dummy):
    try:   
        bpy.types.SpaceView3D.draw_handler_remove(handles[0], 'WINDOW')
        if bpy.context.scene.arp_debug_mode:
            print('Removed handler')
    except:
        if bpy.context.scene.arp_debug_mode:
            print('No handler to remove')
            

#enable markers fx if any markers already in the scene when loading the file
@persistent
def enable_markers_fx(dummy):
    if get_object('arp_markers') is not None:
        if len(get_object('arp_markers').children) > 0:
            print('Markers already in scene, enable Markers FX')
            bpy.ops.id.markers_fx(active=True)
            
            
def update_smart_presets(self, context):
    scn = context.scene
    
    if scn.arp_smart_preset_settings == 'DEFAULT':
        scn.arp_smart_neck_count = 1
        scn.arp_smart_spine_count = 3
        scn.arp_smart_twist_count = 1
        scn.arp_smart_root_vertical = True
        scn.arp_smart_shoulders_align = 'MODEL_FIT'
        scn.arp_smart_spine_shape = 'MODEL_FIT'

    elif scn.arp_smart_preset_settings == 'UE4':
        scn.arp_smart_neck_count = 1
        scn.arp_smart_spine_count = 4
        scn.arp_smart_twist_count = 1
        scn.arp_smart_root_vertical = True
        scn.arp_smart_shoulders_align = 'MODEL_FIT'
        scn.arp_smart_spine_shape = 'ARCHED'
        
    elif scn.arp_smart_preset_settings == 'UE5':
        scn.arp_smart_neck_count = 2
        scn.arp_smart_spine_count = 6
        scn.arp_smart_twist_count = 2
        scn.arp_smart_root_vertical = True
        scn.arp_smart_shoulders_align = 'TILTED'
        scn.arp_smart_spine_shape = 'ARCHED'


def update_facial_list(verts_list, prop):    
    obj = get_object('arp_facial_setup')
    if obj:
        try:
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
        except:
            pass
        set_active_object('arp_facial_setup')   
        bpy.ops.object.mode_set(mode='OBJECT')
        
        for vert in obj.data.vertices:
            if vert.index in verts_list:
                vert.hide = False if prop else True
                
        for edge in obj.data.edges:
            for vi in edge.vertices:
                if vi in verts_list:
                    edge.hide = False if prop else True
                
        bpy.ops.object.mode_set(mode='EDIT')
        
        
def update_smart_ears(self, context):
    scn = bpy.context.scene
    ear_verts = [ard.facial_markers[i] for i in ard.facial_markers if i.startswith('ear_')]
    update_facial_list(ear_verts, scn.arp_smart_ears)
    
         
def update_smart_eyebrows(self, context):
    scn = bpy.context.scene
    eyebrow_verts = [ard.facial_markers[i] for i in ard.facial_markers if i.startswith('eyebrow_')]
    update_facial_list(eyebrow_verts, scn.arp_smart_eyebrows)
   
        
def update_smart_nose(self, context):
    scn = bpy.context.scene
    nose_verts = [ard.facial_markers[i] for i in ard.facial_markers if i.startswith('nose_')]
    update_facial_list(nose_verts, scn.arp_smart_nose)
        

def update_smart_cheeks(self, context):
    scn = bpy.context.scene
    cheek_verts = [ard.facial_markers[i] for i in ard.facial_markers if i.startswith('cheek_')]
    update_facial_list(cheek_verts, scn.arp_smart_cheeks)
    
    
def update_smart_eyes(self, context):
    scn = bpy.context.scene
    eyelid_verts = [ard.facial_markers[i] for i in ard.facial_markers if i.startswith('eyelid_')]
    update_facial_list(eyelid_verts, scn.arp_smart_eyes)
    
def update_smart_mouth(self, context):
    scn = bpy.context.scene
    mouth_verts = [ard.facial_markers[i] for i in ard.facial_markers if i.startswith('lips_')]
    update_facial_list(mouth_verts, scn.arp_smart_mouth)
    
def update_smart_chin(self, context):
    scn = bpy.context.scene
    chin_verts = [ard.facial_markers[i] for i in ard.facial_markers if i.startswith('chin_')]
    update_facial_list(chin_verts, scn.arp_smart_chin)
        
        
bpy.app.handlers.load_pre.append(cleanup)
bpy.app.handlers.load_post.append(enable_markers_fx)


###########  REGISTER  ##################
classes = (ARP_OT_facial_setup, ARP_OT_cancel_facial_setup, ARP_OT_validate_facial_setup, ARP_OT_restore_markers, ARP_OT_turn, 
            ARP_OT_get_selected_objects, 
            ARP_OT_go_detect, ARP_OT_markers_fx, ARP_OT_add_marker, ARP_OT_delete_detected, ARP_MT_optional_markers_menu, ARP_OT_cancel_and_delete_markers, 
            ARP_OT_guess_markers, ARP_OT_guess_fingers, ARP_OT_guess_facial,
            ARP_PT_proxy_utils_ui, bone_transform, markers_transform, facial_markers_transform)#ARP_OT_smart_find_armatures)


def update_arp_tab():
    try:
        bpy.utils.unregister_class(ARP_PT_proxy_utils_ui)
    except:
        pass
    ARP_PT_proxy_utils_ui.bl_category = get_prefs().arp_tab_name
    bpy.utils.register_class(ARP_PT_proxy_utils_ui)

    

def register():
    from bpy.utils import register_class
    for cls in classes:
        try: register_class(cls)
        except: pass

    update_arp_tab()
    
    global custom_icons
    custom_icons = auto_rig.custom_icons
    
    global pcoll
    pcoll = bpy.utils.previews.new()
    file_dir = os.path.dirname(__file__)    
    icons_dir = os.path.join(os.path.dirname(file_dir), 'icons')
    for file_name in os.listdir(icons_dir):
        if file_name.endswith('.png') and (file_name.startswith('fingers') or file_name.startswith('marker_')):
            pcoll.load(file_name.replace('.png', ''), os.path.join(icons_dir, file_name), 'IMAGE')
    bpy.types.Scene.arp_large_icon = bpy.props.IntProperty(default=0)

    bpy.types.Scene.arp_body_name = StringProperty(name="Body name", description = "Get the body object name", options={'HIDDEN'})
    bpy.types.Scene.arp_fingers_to_detect = IntProperty(description = "How many fingers should be found on this model", name="Fingers Detection", default=5, min=0, max=5, update=update_fingers_to_detect, options={'HIDDEN'})
    bpy.types.Scene.arp_fingers_enable = BoolProperty(description="Enable fingers", name = "Enable Fingers", update=update_fingers_enable, default=True, options={'HIDDEN'})
    bpy.types.Scene.arp_fingers_init_transform = CollectionProperty(type=bone_transform)
    bpy.types.Scene.arp_quit = BoolProperty(name="Quit", default=False)
    bpy.types.Scene.arp_markers_save = CollectionProperty(type=markers_transform)
    bpy.types.Scene.arp_facial_markers_save = CollectionProperty(type=facial_markers_transform)
    bpy.types.Scene.arp_smart_depth = BoolProperty(name='Use Markers Depth', default=False, description='Use the markers depth (Y loc)')
    bpy.types.Scene.arp_smart_sym = BoolProperty(name="Mirror", default=True, update=update_sym, description="Mirror the left (character's left side) markers and bones position to the right side", options={'HIDDEN'})
    bpy.types.Scene.arp_foot_dir_l = FloatVectorProperty(name="Left Foot Direction", subtype='DIRECTION', default=(0,0,0))
    bpy.types.Scene.arp_foot_dir_r = FloatVectorProperty(name="Right Foot Direction", subtype='DIRECTION', default=(0,0,0))
    bpy.types.Scene.arp_smart_remesh  = IntProperty(name="Voxel Precision", description = "Voxel resolution for the fingers detection. Should generally not be modified, unless it gives wrong fingers detection.", default=9, soft_min=7, soft_max=10, options={'HIDDEN'})
    bpy.types.Scene.arp_smart_remesh_type  = EnumProperty(items=(('type1', 'Voxel Type 1', 'Type 1'), ('type2', 'Voxel Type 2', 'Type 2')), description="Method to voxelize the model, changing it may improve the results", options={'HIDDEN'})
    bpy.types.Scene.arp_finger_thickness = FloatProperty(name="Finger Thickness", description = "Increase this value if the detected fingers roots position are wrong, if they go too much inward the palm", default=3.0, min=0.5, max=9.0, options={'HIDDEN'})
    bpy.types.Scene.arp_marker_to_select = StringProperty(name="Marker to select")
    bpy.types.Scene.arp_smart_spine_count = IntProperty(name="Spine Count", description="Number of spine bones", default=4, min=1, max=32, options={'HIDDEN'})
    bpy.types.Scene.arp_smart_neck_count = IntProperty(name="Neck Count", description="Number of neck bones", default=1, min=1, max=16, options={'HIDDEN'})
    bpy.types.Scene.arp_smart_twist_count = IntProperty(name="Twist Count", description="Number of twist bones for the arms and legs", default=1, min=1, max=32, options={'HIDDEN'})
    bpy.types.Scene.arp_smart_root_vertical = BoolProperty(name="Root Up", description="Set the spine root bone vertically aligned", default=True, options={'HIDDEN'})
    bpy.types.Scene.arp_smart_spine_shape = EnumProperty(name="Spine Shape", items=(
        ('STRAIGHT', 'Straight', 'Straight spine bones'), 
        ('MODEL_FIT', 'Model Fit', 'Spine bones will fit the model shape'), 
        ('ARCHED', 'Arched (UE)', 'Curved spine, inward. Fit the UE5 Mannequin')), 
        description='Shape of the spine', default='STRAIGHT', options={'HIDDEN'})
    bpy.types.Scene.arp_smart_shoulders_align = EnumProperty(items=(
        ('MODEL_FIT', 'Model Fit', 'Align the clavicles with default position, fitting the pose of the model'),
        ('STRAIGHT', 'Straight', 'Align the Y clavicles location with the arm position'),
        ('TILTED', 'Tilted (UE)', 'Tilt slightly the clavicles down')),
        name="Align Clavicles", description='How to align shoulders/clavicles', default='STRAIGHT', options={'HIDDEN'})
    bpy.types.Scene.arp_smart_overwrite = BoolProperty(name="Overwrite Existing Rig", description="If enabled, overwrite bones data of the existing rig (if any).\nIf disabled, a new rig will always be generated", default=True, options={'HIDDEN'})
    bpy.types.Scene.arp_smart_type = EnumProperty(items=(('BODY', 'Full Body', 'Body, with optional facial'), ('FACIAL', 'Facial Only', 'Facial only')), options={'HIDDEN'})
    bpy.types.Scene.arp_smart_preset_settings = EnumProperty(items=(('DEFAULT', 'ARP Default', 'Default settings'), ('UE4', 'UE4 Mannequin', 'UE4 humanoid skeleton'), ('UE5', 'UE5 Manny-Quinn', 'UE5 humanoid skeleton')), description='Preset settings', update=update_smart_presets, options={'HIDDEN'})
    bpy.types.Scene.arp_smart_eye_shape = EnumProperty(items=( ('SPHERE', 'Sphere', 'The eyeball object is a complete sphere'), ('HEMISPHERE', 'Hemisphere', 'The eyeball object is one half of a sphere') ), description='Eyeball object shape')
    bpy.types.Scene.arp_smart_ears = BoolProperty(default=True, description='Enable ears', update=update_smart_ears, options={'HIDDEN'})
    bpy.types.Scene.arp_smart_eyebrows = BoolProperty(default=True, description='Enable eyebrows', update=update_smart_eyebrows, options={'HIDDEN'})
    bpy.types.Scene.arp_smart_nose = BoolProperty(default=True, description='Enable nose', update=update_smart_nose, options={'HIDDEN'})
    bpy.types.Scene.arp_smart_cheeks = BoolProperty(default=True, description='Enable cheeks', update=update_smart_cheeks, options={'HIDDEN'})
    bpy.types.Scene.arp_smart_eyes = BoolProperty(default=True, description='Enable eyes', update=update_smart_eyes, options={'HIDDEN'})
    bpy.types.Scene.arp_smart_mouth = BoolProperty(default=True, description='Enable mouth', update=update_smart_mouth, options={'HIDDEN'})
    bpy.types.Scene.arp_smart_tongue = BoolProperty(default=True, description='Enable tongue', options={'HIDDEN'})
    bpy.types.Scene.arp_smart_teeth = BoolProperty(default=True, description='Enable teeth', options={'HIDDEN'})
    bpy.types.Scene.arp_smart_chin = BoolProperty(default=True, description='Enable chin', update=update_smart_chin, options={'HIDDEN'})
    bpy.types.Scene.arp_smart_AI_is_installed = BoolProperty(default=False, description='AI folder exists', options={'HIDDEN'})
    bpy.types.Scene.arp_smart_fingers_engine = EnumProperty(items=(
        ('AI', 'AI', 'All-rounder AI detection'),
        ('LEGACY', 'Voxel Centroid', 'Works best with slick fingers topology. Prone to errors with complex, layered topology')
        ), 
        description='Engine to detect fingers', update=update_fingers_engine, default='LEGACY', options={'HIDDEN'})
    bpy.types.Scene.arp_smart_AI_samples = IntProperty(min=2, soft_max=16, default=10, description="More samples = better estimation, may take more time to compute", options={'HIDDEN'})
    bpy.types.Scene.arp_smart_AI_body_samples = IntProperty(min=1, default=10, max=30, description="More samples = better estimation, may take more time to compute", options={'HIDDEN'})
    bpy.types.Scene.arp_smart_AI_facial_samples = IntProperty(min=1, default=8, max=16, description="More samples = better estimation, may take more time to compute", options={'HIDDEN'})
    bpy.types.Scene.arp_smart_AI_thresh = FloatProperty(soft_min=0.1, soft_max=0.7, default=0.5, description="Decreasing this value may help with complex fingers, but more prone to error", options={'HIDDEN'})
   

def unregister():
    global pcoll
    bpy.utils.previews.remove(pcoll)
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)

    del bpy.types.Scene.arp_body_name
    del bpy.types.Scene.arp_fingers_to_detect
    del bpy.types.Scene.arp_fingers_init_transform
    del bpy.types.Scene.arp_quit
    del bpy.types.Scene.arp_markers_save
    del bpy.types.Scene.arp_facial_markers_save
    del bpy.types.Scene.arp_smart_sym
    del bpy.types.Scene.arp_smart_depth
    del bpy.types.Scene.arp_foot_dir_l
    del bpy.types.Scene.arp_foot_dir_r
    del bpy.types.Scene.arp_smart_remesh
    del bpy.types.Scene.arp_smart_remesh_type
    del bpy.types.Scene.arp_finger_thickness
    del bpy.types.Scene.arp_marker_to_select
    del bpy.types.Scene.arp_smart_spine_count
    del bpy.types.Scene.arp_smart_neck_count
    del bpy.types.Scene.arp_smart_twist_count
    del bpy.types.Scene.arp_smart_root_vertical
    del bpy.types.Scene.arp_smart_spine_shape
    del bpy.types.Scene.arp_smart_shoulders_align
    del bpy.types.Scene.arp_smart_overwrite
    del bpy.types.Scene.arp_smart_type
    del bpy.types.Scene.arp_smart_preset_settings
    del bpy.types.Scene.arp_smart_eye_shape
    del bpy.types.Scene.arp_smart_ears
    del bpy.types.Scene.arp_smart_eyebrows
    del bpy.types.Scene.arp_smart_nose
    del bpy.types.Scene.arp_smart_cheeks
    del bpy.types.Scene.arp_smart_eyes
    del bpy.types.Scene.arp_smart_mouth    
    del bpy.types.Scene.arp_smart_tongue
    del bpy.types.Scene.arp_smart_teeth
    del bpy.types.Scene.arp_smart_chin
    del bpy.types.Scene.arp_smart_AI_is_installed
    del bpy.types.Scene.arp_smart_fingers_engine
    del bpy.types.Scene.arp_smart_AI_samples
    del bpy.types.Scene.arp_smart_AI_body_samples
    del bpy.types.Scene.arp_smart_AI_facial_samples
    del bpy.types.Scene.arp_smart_AI_thresh