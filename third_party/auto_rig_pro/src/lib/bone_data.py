import bpy
from .objects import *

class ARP_BonesData:
    custom_bones_list = []
    softlink_bones = []
    const_interp_bones = []
    excluded_bones = []
    armature_name = ''
   
    def init_values(self):
        self.custom_bones_list = []
        self.softlink_bones = []       
        self.const_interp_bones = []
        self.excluded_bones = []
        
    def collect(self, arm_name):  
        self.armature_name = arm_name
        arm = get_object(self.armature_name)

        self.init_values()
        
        def add_stretch_bones(b):
            # the main stretch arm/leg bones must be added as well in case
            # of Humanoid export and Secondary Controllers set to Twist
            for f in ["arm", "forearm", "thigh", "leg"]:
                s = get_bone_side(b.name)
                if b.name == "c_"+f+"_stretch"+s:
                    self.softlink_bones.append(f+"_stretch"+s)

        # collect props in Edit/Object mode
        for b in arm.data.bones:
            found_bone = False
            if len(b.keys()):
                if "custom_bone" in b.keys() or "cc" in b.keys():
                    found_bone = True

                if "softlink" in b.keys():
                    if not b.name in self.softlink_bones:
                        self.softlink_bones.append(b.name)
                        add_stretch_bones(b)                        
              
                if 'const_interp' in b.keys():
                    if not b.name in self.const_interp_bones:
                        self.const_interp_bones.append(b.name)
                        
                if 'exclude' in b.keys():
                    if not b.name in self.excluded_bones:
                        self.excluded_bones.append(b.name)

            if b.name.startswith("cc_"):
                found_bone = True
            if found_bone and not b.name in self.custom_bones_list:
                self.custom_bones_list.append(b.name)


        if "b" in locals():
            del b

        # also collect props in Pose Mode
        set_active_object(self.armature_name)
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        set_active_object(self.armature_name)
        bpy.ops.object.mode_set(mode='POSE')

        for b in arm.pose.bones:
            if len(b.keys()):
                if "custom_bone" in b.keys() or "cc" in b.keys():
                    if not b.name in self.custom_bones_list:
                        self.custom_bones_list.append(b.name)

                if "softlink" in b.keys():
                    if not b.name in self.softlink_bones:
                        self.softlink_bones.append(b.name)
                        add_stretch_bones(b)                        
            
                if 'const_interp' in b.keys():
                    if not b.name in self.const_interp_bones:
                        self.const_interp_bones.append(b.name)
                        
                if 'exclude' in b.keys():
                    if not b.name in self.excluded_bones:
                        self.excluded_bones.append(b.name)
        
        
    
arp_bones_data = ARP_BonesData()


def is_custom_bone(bone_name):
    return bone_name in arp_bones_data.custom_bones_list
    
    
def exclude_custom_bone(bone_name):
    arp_bones_data.custom_bones_list.remove(bone_name)

    
def is_softlink_bone(bone_name):
    return bone_name in arp_bones_data.softlink_bones
    
    
def is_const_interp_bone(bone_name):
    return bone_name in arp_bones_data.const_interp_bones
    
    
def is_excluded_bone(bone_name):
    return bone_name in arp_bones_data.excluded_bones
    
    
def get_renamed_bone(bone_name):
    if bone_name in arp_bones_data.renamed_bones:
        return arp_bones_data.renamed_bones[bone_name]
    return ''


def get_bone_base_name(bone_name):
    base_name = bone_name[:-2]# head.x > head
    if "_dupli_" in bone_name:
        base_name = bone_name[:-12]
    return base_name


def retarget_bone_side(bone_name, target_side, dupli_only=False):#"head.x", "_dupli_001.x"
    current_side = get_bone_side(bone_name)#'.x'
    base_name = get_bone_base_name(bone_name)#'head'
    new_name = ""
        
    if dupli_only:# we only want to set the dupli ID and preserve the left/right/center side suffix
        current_side_letters = bone_name[-2:]#.l
        dupli_side = target_side[:-2]#'_dupli_001' or ''
        new_name = base_name+dupli_side+current_side_letters #'eyelid'+'_dupli_001'+'.l'        
    else:        
        new_name = base_name+target_side#'head'+'_dupli_001.x'
    
    #if bone_name != new_name:
    #    print("retarget bone side", bone_name, new_name)
        
    return new_name
    
    
def get_bone_side(bone_name):
    side = ""
    if not "_dupli_" in bone_name:
        side = bone_name[-2:]
    else:
        side = bone_name[-12:]
    return side
    
    
def get_opposite_side(side):
    if side.endswith('.l'):
        return side[:-2] + '.r'
    elif side.endswith('.r'):
        return side[:-2] + '.l'
    else:
        return ''


def get_data_bone(bonename):
    return bpy.context.active_object.data.bones.get(bonename)


def duplicate(type=None):
    # runs the operator to duplicate the selected objects/bones
    if type == "EDIT_BONE":
        bpy.ops.armature.duplicate_move(ARMATURE_OT_duplicate={}, TRANSFORM_OT_translate={"value": (0.0, 0.0, 0.0), "constraint_axis": (False, False, False),"orient_type": 'LOCAL', "mirror": False, "use_proportional_edit": False, "snap": False, "remove_on_cancel": False, "release_confirm": False})
    elif type == "OBJECT":
        bpy.ops.object.duplicate(linked=False, mode='TRANSLATION')
        
        
def get_bone_children(b):
    children_list = []
    children_list = get_bone_children_recur(b, list=children_list)
    return children_list
    
    
def get_bone_children_recur(b, list=None):
    if b.children:
        for child in b.children:          
            list.append(child)            
            get_bone_children_recur(child, list=list)
    return list