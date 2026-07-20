# ***** BEGIN GPL LICENSE BLOCK *****
#
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ***** END GPL LICENCE BLOCK *****


bl_info = {
    "name": "Auto-Rig Pro",
    "author": "Artell",
    "version": (3, 78, 34),
    "blender": (4, 2, 0),
    "location": "3D View > Properties> Auto-Rig Pro",
    "description": "Automatic rig generation based on reference bones and various tools",
    "tracker_url": "http://lucky3d.fr/auto-rig-pro/doc/bug_report.html", 
    "doc_url": "http://lucky3d.fr/auto-rig-pro/doc/",
    "category": "Rigging",
    }


import bpy, shutil
from bpy.app.handlers import persistent
from .src import auto_rig_prefs
from .src import rig_functions
from .src import auto_rig
from .src import auto_rig_smart
from .src import auto_rig_remap
from .src import auto_rig_ge
if bpy.app.version >= (4,1,0):
    from .src.export_fbx import arp_fbx_init
else:
    from .src.export_fbx_old import arp_fbx_init
from .src import utils
 

# gltf export specials 
if bpy.app.version >= (4, 4, 0):
    from .src.lib.animation import get_action_slot_idx
    
    
class glTF2ExportUserExtension:
    
    export_action_only = ''
    
    def __init__(self):
        self.base_action = None
        self.base_action_slot_idx = 0
        

    def gather_actions_hook(self, blender_object, params, export_settings):  
        # This hook collects exportable baked actions
        
        # Filter actions
        #   Only filter ARP rigs
        if not 'arp_rig_name' in blender_object:
            return
        
        # convert string list with fancy separators to list
        export_actions_names = []
        sep = '|%%|'
        print('export_action_only', self.export_action_only)
        if sep in self.export_action_only:
            for actname in self.export_action_only.split(sep):
                export_actions_names.append(actname)
        
        if len(export_actions_names):
            print('Actions:', export_actions_names)
        
        # collection actions
        act_list = []       

        if bpy.app.version >= (4, 4, 0):
            # With version 4.4.0 and higher, params is an object that contains all needed data
            for action_id in list(params.actions.keys()):
                for act_id, act in enumerate(params.actions[action_id][:]):
                    if "arp_baked_action" in act.action.keys():
                        if self.export_action_only == 'all_actions':
                            pass  # Do nothing, all actions are exported
                        elif len(export_actions_names) == 0 and self.export_action_only == params.actions[action_id][act_id].action.name:# single action
                            pass
                        elif len(export_actions_names) and params.actions[action_id][act_id].action.name in export_actions_names:# multiple actions
                            pass  # Do nothing, this action is exported
                        else:
                            # We are going to remove this action from the list
                            params.actions[action_id].remove(act)
                    else:
                        params.actions[action_id].remove(act)
        else:
            # With version previous to 4.4.0, params has 3 fields: blender_actions, blender_tracks, action_on_type                       
            for act in params.blender_actions:
                if len(act.keys()):
                    if "arp_baked_action" in act.keys(): 
                        if self.export_action_only == 'all_actions':# all
                            act_list.append(act)  
                        elif self.export_action_only == act.name:# single action export
                            act_list.append(act)
                        elif len(export_actions_names):# actions list export
                            if act.name in export_actions_names:
                                act_list.append(act)
   
        params.blender_actions = act_list
        
        for (k, v) in params.blender_tracks.items():
            print('k', k)
            print('v', v)
        params.blender_tracks = {k:v for (k, v) in params.blender_tracks.items() if k in [act.name for act in params.blender_actions]}
        params.action_on_type = {k:v for (k, v) in params.action_on_type.items() if k in [act.name for act in params.blender_actions]}

        
    def animation_switch_loop_hook(self, blender_object, post, export_settings):
        # This hook ensures that the original rig active action is conserved after exporting, since it is switched during the export
        
        # Store active action of original rig before looping through actions        
        if 'arp_rig_name' in blender_object and post is False:
            original_rig = bpy.data.objects[blender_object['arp_rig_name']]
            if original_rig.animation_data and original_rig.animation_data.action:
                # save action
                self.base_action = original_rig.animation_data.action
                
                # save slot
                if bpy.app.version >= (4,4,0):# backward-compatibility
                    self.base_action_slot_idx = get_action_slot_idx(self.base_action, original_rig.animation_data.action_slot)

        # Restore initial action of the original rig
        # After looping on actions to export
        if 'arp_rig_name' in blender_object and post is True:
            original_rig = bpy.data.objects[blender_object['arp_rig_name']]
            if original_rig.animation_data:
                # assign action
                original_rig.animation_data.action = self.base_action
                
                # assign slot
                if bpy.app.version >= (4, 4, 0):
                    original_rig.animation_data.action_slot = self.base_action.slots[self.base_action_slot_idx]
                    
            self.base_action = None
            self.base_action_slot_idx = 0
            
    
    def post_animation_switch_hook(self, *args, **kwargs):
        # This hook is necessary for shape keys export
        # (if shape keys are driven by bones, then contained in the action data)
        # When switching the exported rig action, make sure to also switch the action of the original rig

        # the original action name and slot index are now stored in the 'arp_baked_action' property located on the baked action:
        # ["arp_baked_action"] = action.name+'|||'+str(slot_idx)
        # to be fetched with:
        # act_name, slot_idx = blender_action["arp_baked_action"].split('|||')

        if bpy.app.version >= (4, 4, 0):
            blender_object, blender_action, slot, track_name, on_type, export_settings = args
        else:
            blender_object, blender_action, track_name, on_type, export_settings = args

        if 'arp_rig_name' in blender_object:
            original_rig = bpy.data.objects[blender_object['arp_rig_name']]
            if original_rig.animation_data:
                act_name, slot_idx = blender_action["arp_baked_action"].split('|||')
                
                # assign action
                original_rig.animation_data.action = bpy.data.actions[act_name]
                
                # assign slot
                if bpy.app.version >= (4, 4, 0):
                    original_rig.animation_data.action_slot = \
                        original_rig.animation_data.action.slots[int(slot_idx)]
                
                
def menu_func_export(self, context):
    self.layout.operator(auto_rig_ge.ARP_OT_GE_export_fbx_panel.bl_idname, text="Auto-Rig Pro FBX (.fbx)")
    if bpy.app.version >= (3, 4, 0):
        self.layout.operator(auto_rig_ge.ARP_OT_GE_export_gltf_panel.bl_idname, text="Auto-Rig Pro GLTF (.glb/.gltf)")    
    

def cleanse_modules():
    import sys
    all_modules = sys.modules 
    all_modules = dict(sorted(all_modules.items(),key= lambda x:x[0]))
    for k in all_modules:
        if k.startswith(__name__):
            del sys.modules[k]


def register():
    auto_rig_prefs.register()
    auto_rig.register()
    auto_rig_smart.register()   
    auto_rig_remap.register()
    auto_rig_ge.register()
    rig_functions.register()
    arp_fbx_init.register()
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)   
    

def unregister():
    auto_rig_prefs.unregister()
    auto_rig.unregister()
    auto_rig_smart.unregister() 
    auto_rig_remap.unregister()
    auto_rig_ge.unregister()
    rig_functions.unregister()
    arp_fbx_init.unregister()
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)        
    cleanse_modules()
    

if __name__ == "__main__":
    register()