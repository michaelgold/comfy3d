import bpy
from .version import *

def is_action_baked(action):
    # check if the action is a baked one, for either humanoid or universal skeleton
    scn = bpy.context.scene
    
    if scn.arp_export_rig_type == 'HUMANOID' or scn.arp_export_rig_type == 'UNIVERSAL':
        if scn.arp_bake_anim and check_id_root(action):
            if len(action.keys()):
                if "arp_baked_action" in action.keys():                      
                    return True
    return False
    
    
def is_action_exportable(action):
    # check if the action is marked as exportable
    if len(action.keys()):
        if 'arp_export' in action.keys():
            return action['arp_export']
    return True