import bpy
import mathutils
from mathutils import *

doc_url = 'https://lucky3d.fr/auto-rig-pro/doc/'
discord_url = 'https://discord.gg/Cu7XwVyDn'

# Layers to collection data conversion
layer_col_map_special = {'ge_childof':16, 'ge_orient':17, 'ge_basebone':18, 'remap01':24, 'mch_feathers':24, 'mch_kilt_masters':24, 'remap02':25, 'mch_3bik_2':25}
layer_col_map = {'Main':0, 'Secondary':1, 'mch_01':8, 'mch_stretch':9, 'mch_base':10, 'mch_twist':11, 'mch_ik':12, 
                'mch_ik_nostr':13, 'mch_fk':14, 'Reference':17, 'mch_disabled':22, 'mch_cs_transf':23,
                'mch_3bik_2_nostr':29, 'mch_3bik_2_rev':28, 'mch_cor_sk':30, 'Deform':31}
                
bones_groups = ['secondary', 'hair', 'body.r', 'body.l', 'hidden', 'hand.l', 'hand.r', 'body.r_sel', 'body.l_sel', 'body.x_sel', 'body.x']
bones_groups_to_remove = ['secondary', 'hair', 'hidden', 'hand.l', 'hand.r', 'body.l_sel', 'body.x_sel', 'body.r_sel', 'ik_target.l', 'ik_target.r', 'ik_target2.l', 'ik_target2.r', 'ik_pole.l', 'ik_pole.r', 'red']


# ARMS
#   Fingers
fingers_names = ['pinky', 'ring', 'index', 'middle', 'thumb']

#     thumb
thumb_ref_dict = {'thumb1':'thumb1_ref', 'thumb2':'thumb2_ref', 'thumb3':'thumb3_ref'}
thumb_ref_list = [j for i, j in thumb_ref_dict.items()]

thumb_control_dict = {'base':'c_thumb1_base', '1':'c_thumb1', '2':'c_thumb2', '3':'c_thumb3'}
thumb_control_list = [j for i, j in thumb_control_dict.items()]

thumb_intern_dict = {'base':'thumb1', 'bend_all':'thumb_bend_all', 'rot1':'thumb1_rot', 'rot2':'thumb2_rot', 'rot3':'thumb3_rot'}
thumb_intern_list = [j for i, j in thumb_intern_dict.items()]

#    index
index_ref_dict = {'index_meta':'index1_base_ref', 'index1':'index1_ref', 'index2':'index2_ref', 'index3':'index3_ref'}
index_ref_list = [j for i, j in index_ref_dict.items()]

index_control_dict = {i: j.replace('thumb', 'index') for i, j in thumb_control_dict.items()}
index_control_list = [j for i, j in index_control_dict.items()]

index_intern_dict = {i: j.replace('thumb','index') for i, j in thumb_intern_dict.items()}
index_intern_list = [j for i, j in index_intern_dict.items()]

#    middle
middle_ref_dict = {'middle_meta':'middle1_base_ref', 'middle1':'middle1_ref', 'middle2':'middle2_ref', 'middle3':'middle3_ref'}
middle_ref_list = [j for i, j in middle_ref_dict.items()]

middle_control_dict = {i: j.replace('thumb', 'middle') for i, j in thumb_control_dict.items()}
middle_control_list = [j for i, j in middle_control_dict.items()]

middle_intern_dict = {i: j.replace('thumb','middle') for i, j in thumb_intern_dict.items()}
middle_intern_list = [j for i, j in middle_intern_dict.items()]

#    ring
ring_ref_dict = {'ring_meta':'ring1_base_ref', 'ring1':'ring1_ref', 'ring2':'ring2_ref', 'ring3':'ring3_ref'}
ring_ref_list = [j for i, j in ring_ref_dict.items()]

ring_control_dict = {i: j.replace('thumb', 'ring') for i, j in thumb_control_dict.items()}
ring_control_list = [j for i, j in ring_control_dict.items()]

ring_intern_dict = {i: j.replace('thumb','ring') for i, j in thumb_intern_dict.items()}
ring_intern_list = [j for i, j in ring_intern_dict.items()]

#    pinky
pinky_ref_dict = {'pinky_meta':'pinky1_base_ref', 'pinky1':'pinky1_ref', 'pinky2':'pinky2_ref', 'pinky3':'pinky3_ref'}
pinky_ref_list = [j for i, j in pinky_ref_dict.items()]

pinky_control_dict = {i: j.replace('thumb', 'pinky') for i, j in thumb_control_dict.items()}
pinky_control_dict['pinky_auto'] = 'c_pinky1_auto'
pinky_control_list = [j for i, j in pinky_control_dict.items()]

pinky_intern_dict = {i: j.replace('thumb','pinky') for i, j in thumb_intern_dict.items()}
pinky_intern_list = [j for i, j in pinky_intern_dict.items()]


fingers_control = thumb_control_list + index_control_list + middle_control_list + ring_control_list + pinky_control_list
fingers_intern = thumb_intern_list + index_intern_list + middle_intern_list + ring_intern_list + pinky_intern_list

#     ik
fingers_control_ik = []
for finger_type in ['thumb', 'index', 'middle', 'ring', 'pinky']:
    for fi in range(1, 4):
        fingers_control_ik.append('c_'+finger_type+str(fi)+'_ik')
        fingers_control_ik.append('c_'+finger_type+str(fi)+'_ik3')
    
    fingers_control_ik.append('c_'+finger_type+'_ik')# target
    fingers_control_ik.append('c_'+finger_type+'_ik2')
    fingers_control_ik.append('c_'+finger_type+'_pole')# pole
    

#   Arms
arm_bones_dict = {
    'shoulder':{'control':'c_shoulder', 'deform':'shoulder', 'track_pole':'shoulder_track_pole', 'pole':'shoulder_pole'},
    'arm':{'base':'arm', 'twist':'arm_twist', 'twist_twk':'arm_twist_twk', 'control_twist':'c_arm_twist_offset', 'stretch':'arm_stretch', 'control_fk':'c_arm_fk', 'fk':'arm_fk', 'ik':'arm_ik', 'control_ik':'c_arm_ik', 'ik_scale_fix':'arm_ik_nostr_scale_fix', 'ik_nostr':'arm_ik_nostr', 'secondary_00':'c_shoulder_bend','secondary_01':'c_arm_bend'},
    'forearm':{'base':'forearm', 'control_fk':'c_forearm_fk', 'fk':'forearm_fk', 'ik':'forearm_ik', 'ik_nostr':'forearm_ik_nostr', 'stretch':'forearm_stretch', 'twist':'forearm_twist', 'secondary_00':'c_elbow_bend', 'secondary_01':'c_forearm_bend', 'secondary_02':'c_wrist_bend'},
    'hand':{'deform':'hand', 'control_fk':'c_hand_fk', 'control_ik':'c_hand_ik', 'control_ik_offset':'c_hand_ik_offset', 'ik_pivot':'hand_ik_pivot', 'control_ik_pivot':'c_hand_ik_pivot', 'fk_scale_fix':'hand_fk_scale_fix', 'rot_twist':'hand_rot_twist', 'secondary_00':'hand_bend'},
    'prepole':'arm_fk_pre_pole',
    'fk_pole':'arm_fk_pole',
    'control_pin':'c_stretch_arm_pin',
    'control_stretch':'c_stretch_arm',
    'control_pole_ik': 'c_arms_pole',
    'pole_line': 'arm_pole_line'}
    
arm_bones = []
for i, j in arm_bones_dict.items():
    if type(j) is dict:
        for k, l in j.items():
            arm_bones.append(l)            
    else:
        arm_bones.append(j)
        
# add fingers
arm_bones = arm_bones + fingers_control + fingers_intern

arm_ref_dict = {'shoulder':'shoulder_ref', 'arm':'arm_ref', 'forearm':'forearm_ref', 'hand':'hand_ref', **thumb_ref_dict, **index_ref_dict, **middle_ref_dict, **ring_ref_dict, **pinky_ref_dict}

arm_ref_list = [j for i, j in arm_ref_dict.items()]

arm_bones_rig_add = [arm_bones_dict['arm']['secondary_00'], arm_bones_dict['arm']['secondary_01'], arm_bones_dict['forearm']['secondary_00'], arm_bones_dict['forearm']['secondary_01'], arm_bones_dict['forearm']['secondary_02'], arm_bones_dict['hand']['secondary_00']]

arm_deform = [arm_bones_dict['shoulder']['deform'], arm_bones_dict['arm']['control_twist'], arm_bones_dict['arm']['stretch'], arm_bones_dict['forearm']['twist'], arm_bones_dict['forearm']['stretch'], arm_bones_dict['hand']['deform']]

arm_control = [arm_bones_dict['hand']['control_ik'], arm_bones_dict['hand']['control_fk'], arm_bones_dict['arm']['control_fk'], arm_bones_dict['arm']['control_ik'], arm_bones_dict['forearm']['control_fk'], arm_bones_dict['shoulder']['control'], arm_bones_dict['arm']['control_twist'], arm_bones_dict['control_pole_ik'], arm_bones_dict['arm']['secondary_00'], arm_bones_dict['arm']['secondary_01'], arm_bones_dict['forearm']['secondary_00'], arm_bones_dict['forearm']['secondary_01'], arm_bones_dict['forearm']['secondary_02'], arm_bones_dict['control_stretch'], arm_bones_dict['control_pin']]

arm_bendy_dict = {'arm':'arm_bendy', 'forearm':'forearm_bendy'}

arm_props = {'soft_ik': 'arm_softik', 'auto_ik_roll': 'arm_auto_ik_roll'}


def get_arm_joint_fans(arm_side, btype='ALL', no_side=False):
    types = [btype]    
    if btype == 'ALL':
        types = ['CONTROLLER', 'ROT', 'TAR']   
        
    list = []

    for subtype in types:
        for i in range(1,32):
            for lvl in ['elbow_in', 'elbow_out', 'wrist_in', 'wrist_out']:
                bname = ''            
                if subtype == 'CONTROLLER':
                    bname = 'c_'+lvl+'_'+'%02d' % i +arm_side
                elif subtype == 'ROT':
                    bname = lvl+'_rot_'+'%02d' % i+arm_side
                elif subtype == 'TAR':
                    bname = lvl+'_tar_'+'%02d' % i+arm_side
             
                if bpy.context.active_object.data.bones.get(bname):
                    if no_side:
                        bname = bname.replace(arm_side, '')
                    list.append(bname)
                    
    return list



# LEGS
#   toes
toes_thumb_ref_dict = {'toes_thumb1':'toes_thumb1_ref', 'toes_thumb2':'toes_thumb2_ref', 'toes_thumb_meta':'toes_thumb1_base_ref'}
toes_thumb_ref_list = [j for i, j in toes_thumb_ref_dict.items()]
toes_thumb_control_dict = {'1': 'c_toes_thumb1', '2':'c_toes_thumb2'}
toes_thumb_control_list = [j for i, j in toes_thumb_control_dict.items()]

toes_index_ref_dict = {'toes_index1':'toes_index1_ref', 'toes_index2':'toes_index2_ref', 'toes_index3':'toes_index3_ref', 'toes_index_meta':'toes_index1_base_ref'}
toes_index_ref_list = [j for i, j in toes_index_ref_dict.items()]
toes_index_control_dict = {'1': 'c_toes_index1', '2':'c_toes_index2', '3':'c_toes_index3'}
toes_index_control_list = [j for i, j in toes_index_control_dict.items()]

toes_middle_ref_dict = {'toes_middle1':'toes_middle1_ref', 'toes_middle2':'toes_middle2_ref', 'toes_middle3':'toes_middle3_ref', 'toes_middle_meta':'toes_middle1_base_ref'}
toes_middle_ref_list = [j for i, j in toes_middle_ref_dict.items()]
toes_middle_control_dict = {i: j.replace('index','middle') for i, j in toes_index_control_dict.items()}
toes_middle_control_list =  [j for i, j in toes_middle_control_dict.items()]

toes_ring_ref_dict = {'toes_ring1':'toes_ring1_ref', 'toes_ring2':'toes_ring2_ref', 'toes_ring3':'toes_ring3_ref', 'toes_ring_meta':'toes_ring1_base_ref'}
toes_ring_ref_list = [j for i, j in toes_ring_ref_dict.items()]
toes_ring_control_dict = {i: j.replace('index','ring') for i, j in toes_index_control_dict.items()}
toes_ring_control_list = [j for i, j in toes_ring_control_dict.items()]

toes_pinky_ref_dict = {'toes_pinky1':'toes_pinky1_ref', 'toes_pinky2':'toes_pinky2_ref', 'toes_pinky3':'toes_pinky3_ref', 'toes_pinky_meta':'toes_pinky1_base_ref'}
toes_pinky_ref_list =  [j for i, j in toes_pinky_ref_dict.items()]
toes_pinky_control_dict = {i: j.replace('index','pinky') for i, j in toes_index_control_dict.items()}
toes_pinky_control_list = [j for i, j in toes_pinky_control_dict.items()]

toes_control = toes_thumb_control_list + toes_index_control_list + toes_middle_control_list + toes_ring_control_list + toes_pinky_control_list


leg_bones_dict = {
    'leg_pole_root': 'leg_pole_root',
    'leg_pole_tracker': 'leg_pole_tracker',
    'leg_pole_prsv_scale': 'leg_pole_psrv',
    'thigh_b_ik':{'1':'thigh_b_ik01', '2':'thigh_b_ik02', '3':'thigh_b_ik03'},
    'upthigh2': 'thigh_b_str',
    'upthigh':'c_thigh_b',    
    'upthigh_helper': {'1': 'thigh_b_h', '2': 'thigh_b_loc'},
    'thigh': {'base':'thigh', 'fk':'thigh_fk', 'ik':'thigh_ik', 'ik_nostr':'thigh_ik_nostr', 'control_fk':'c_thigh_fk', 'control_ik':'c_thigh_ik', 'twist':'thigh_twist', 'stretch':'thigh_stretch', 'secondary_00':'c_thigh_bend_contact', 'secondary_01':'c_thigh_bend_01', 'secondary_02':'c_thigh_bend_02'}, 
    'calf':{'base':'leg', 'fk':'leg_fk', 'ik':'leg_ik', 'ik_nostr':'leg_ik_nostr', 'control_fk':'c_leg_fk', 'control_ik3':'c_leg_ik3', 'twist':'leg_twist', 'stretch':'leg_stretch', 'secondary_00':'c_knee_bend', 'secondary_01':'c_leg_bend_01', 'secondary_02':'c_leg_bend_02', 'secondary_03':'c_ankle_bend'}, 
    'foot':{'fk':'foot_fk', 'control_fk':'c_foot_fk', 'snap_fk':'foot_snap_fk', 'ik':'foot_ik', 'ik_target':'foot_ik_target', 'control_ik':'c_foot_ik', 'deform':'foot', 'pole':'foot_pole', 'fk_scale_fix':'foot_fk_scale_fix', 'shape_override_fk':'c_p_foot_fk', 'shape_override_ik':'c_p_foot_ik', 'bank_01':'foot_bank_01', 'bank_02':'foot_bank_02', 'foot_heel':'foot_heel', 'control_reverse':'c_foot_01', 'pole_01':'foot_01_pole', 'roll':'foot_roll', 'control_roll':'c_foot_roll_cursor', 'secondary_00':'foot_bend', 'ik_pivot':'foot_ik_pivot', 'control_ik_pivot':'c_foot_ik_pivot','control_ik_offset':'c_foot_ik_offset', 'foot_fans_helper':'foot_fans_h'}, 
    'toes':{'01': 'toes_01', '02': 'toes_02', '01_ik': 'toes_01_ik', 'control_fk': 'c_toes_fk', 'control_ik':'c_toes_ik', 'toes_track': 'toes_track', 'toes_end': 'toes_end', 'toes_end_01':'toes_end_01', 'control_pivot':'c_toes_pivot'}, 
    'prepole':'leg_fk_pre_pole', 
    'control_pole_ik':'c_leg_pole',
    'pole_line': 'leg_pole_line',
    'fk_pole':'leg_fk_pole',
    'control_stretch':'c_stretch_leg',
    'control_pin':'c_stretch_leg_pin',
    'toes_pinky1':'c_toes_pinky1', 'toes_pinky2':'c_toes_pinky2', 'toes_pinky3':'c_toes_pinky3', 
    'toes_ring1':'c_toes_ring1', 'toes_ring2':'c_toes_ring2', 'toes_ring3':'c_toes_ring3', 
    'toes_middle1':'c_toes_middle1', 'toes_middle2':'c_toes_middle2', 'toes_middle3':'c_toes_middle3', 
    'toes_index1':'c_toes_index1', 'toes_index2':'c_toes_index2', 'toes_index3':'c_toes_index3', 
    'toes_thumb1':'c_toes_thumb1', 'toes_thumb2':'c_toes_thumb2',
    'toes_thumb_base': 'c_toes_thumb1_base', 
    'toes_index_base': 'c_toes_index1_base', 
    'toes_middle_base': 'c_toes_middle1_base', 
    'toes_ring_base': 'c_toes_ring1_base', 
    'toes_pinky_base': 'c_toes_pinky1_base',
    'toes_pinky_auto': 'c_toes_pinky1_base_auto'
    }

leg_bones_list = []
for i, j in leg_bones_dict.items():
    if type(j) is dict:
        for k, l in j.items():
            leg_bones_list.append(l)
    else:
        leg_bones_list.append(j)
        
    
leg_ref_bones_dict = {'thigh_b':'thigh_b_ref', 'thigh':'thigh_ref', 'calf':'leg_ref', 'foot':'foot_ref',
    'toes':'toes_ref', 'toes_end':'toes_end_ref',
    'heel_bank_01':'foot_bank_01_ref', 'heel_bank_02':'foot_bank_02_ref', 'heel':'foot_heel_ref',
    **toes_thumb_ref_dict, **toes_index_ref_dict, **toes_middle_ref_dict, **toes_ring_ref_dict, **toes_pinky_ref_dict}

leg_ref_bones_list = [j for i, j in leg_ref_bones_dict.items()]

leg_bones_rig_add = [
    leg_bones_dict['calf']['secondary_00'], leg_bones_dict['calf']['secondary_01'], leg_bones_dict['calf']['secondary_02'], leg_bones_dict['calf']['secondary_03'], leg_bones_dict['thigh']['secondary_00'], leg_bones_dict['thigh']['secondary_01'], leg_bones_dict['thigh']['secondary_02'], leg_bones_dict['foot']['secondary_00']]

leg_deform = [
    leg_bones_dict['foot']['deform'], 
    leg_bones_dict['toes_pinky1'], leg_bones_dict['toes_pinky2'], leg_bones_dict['toes_pinky3'], 
    leg_bones_dict['toes_ring1'], leg_bones_dict['toes_ring2'], leg_bones_dict['toes_ring3'], 
    leg_bones_dict['toes_middle1'], leg_bones_dict['toes_middle2'], leg_bones_dict['toes_middle3'], 
    leg_bones_dict['toes_index1'], leg_bones_dict['toes_index2'], leg_bones_dict['toes_index3'], 
    leg_bones_dict['toes_thumb1'], leg_bones_dict['toes_thumb2'], 
    leg_bones_dict['toes_thumb_base'],
    leg_bones_dict['toes_index_base'],
    leg_bones_dict['toes_middle_base'],
    leg_bones_dict['toes_ring_base'],
    leg_bones_dict['toes_pinky_base'],
    leg_bones_dict['toes']['01'], leg_bones_dict['thigh']['twist'], leg_bones_dict['calf']['stretch'], 
    leg_bones_dict['calf']['twist'], leg_bones_dict['thigh']['stretch'], leg_bones_dict['upthigh'],
    leg_bones_dict['upthigh2']]

leg_control = [
    leg_bones_dict['upthigh'], leg_bones_dict['thigh']['control_fk'], leg_bones_dict['thigh']['control_ik'], leg_bones_dict['calf']['control_fk'], leg_bones_dict['toes_pinky1'], leg_bones_dict['toes_pinky2'], leg_bones_dict['toes_pinky3'], leg_bones_dict['toes_ring1'], leg_bones_dict['toes_ring2'], leg_bones_dict['toes_ring3'], leg_bones_dict['toes_middle1'], leg_bones_dict['toes_middle2'], leg_bones_dict['toes_middle3'], leg_bones_dict['toes_index1'], leg_bones_dict['toes_index2'], leg_bones_dict['toes_index3'], leg_bones_dict['toes_thumb1'], leg_bones_dict['toes_thumb2'], leg_bones_dict['foot']['control_fk'], leg_bones_dict['toes']['control_fk'], leg_bones_dict['control_stretch'], leg_bones_dict['calf']['secondary_03'], leg_bones_dict['calf']['secondary_02'], leg_bones_dict['calf']['secondary_01'], leg_bones_dict['calf']['secondary_00'], leg_bones_dict['thigh']['secondary_02'], leg_bones_dict['thigh']['secondary_01'], leg_bones_dict['thigh']['secondary_00'], leg_bones_dict['control_pin'], leg_bones_dict['foot']['control_ik'], leg_bones_dict['foot']['control_ik_offset'], leg_bones_dict['foot']['control_ik_pivot'],leg_bones_dict['toes']['control_ik'], leg_bones_dict['foot']['control_reverse'], leg_bones_dict['foot']['control_roll'], leg_bones_dict['control_pole_ik']]
    

leg_props = {'soft_ik': 'leg_softik', 'auto_ik_roll': 'leg_auto_ik_roll'}


def get_leg_toes_ikfk(leg_side, btype='ALL', no_side=False):
    types = [btype]    
    if btype == 'ALL':
        types = ['FK', 'IK', 'IK_TARGET', 'DEFORM']
        
    list = []

    for subtype in types:
        for i in range(1,4):
            for toe_type in ['thumb', 'index', 'middle', 'ring', 'pinky']:
                bname = ''            
                if subtype == 'FK':
                    bname = 'c_toes_'+toe_type+str(i)+leg_side
                elif subtype == 'IK':
                    bname = 'toes_'+toe_type+str(i)+'_ik'+leg_side
                elif subtype == 'DEFORM':
                    bname = 'toes_'+toe_type+str(i)+'_def'+leg_side
                elif subtype == 'IK_TARGET':
                    if i == 1:
                        bname = 'c_toes_'+toe_type+'_ik_tar'+leg_side
                    
                if bpy.context.active_object.data.bones.get(bname):
                    if no_side:
                        bname = bname.replace(leg_side, '')
                    list.append(bname)
                    
    return list


def get_leg_joint_fans(leg_side, btype='ALL', no_side=False):
    types = [btype]    
    if btype == 'ALL':
        types = ['CONTROLLER', 'ROT', 'TAR']   
        
    list = []

    for subtype in types:
        for i in range(1,32):
            for lvl in ['thigh_in', 'thigh_out', 'knee_in', 'knee_out', 'ankle_in', 'ankle_out']:
                bname = ''            
                if subtype == 'CONTROLLER':
                    bname = 'c_'+lvl+'_'+'%02d' % i +leg_side
                elif subtype == 'ROT':
                    bname = lvl+'_rot_'+'%02d' % i+leg_side
                elif subtype == 'TAR':
                    bname = lvl+'_tar_'+'%02d' % i+leg_side
             
                if bpy.context.active_object.data.bones.get(bname):
                    if no_side:
                        bname = bname.replace(leg_side, '')
                    list.append(bname)
                    
    return list


# HEAD
skulls_dict = {
    '01':'c_skull_01.x',
    '02':'c_skull_02.x',
    '03':'c_skull_03.x'
    }
    
skulls = [j for i, j in skulls_dict.items()]

heads_dict = {
    'deform':'head.x',
    'control':'c_head.x',
    'scale_fix':'head_scale_fix.x',
    'shape_override':'c_p_head.x'
    }
    
head_deform = [heads_dict['deform']] + skulls
head_control = [heads_dict['control']] + skulls
head_bones = [j for i, j in heads_dict.items()] + skulls
head_ref = ['head_ref.x']

#   mouth
mouth_bones_ref_dict = {'lips_top_mid': 'lips_top_ref.x',
                        'lips_top': 'lips_top_ref',
                        'lips_top_01': 'lips_top_01_ref',
                        'lips_smile': 'lips_smile_ref',
                        'lips_corner_mini': 'lips_corner_mini_ref',
                        'lips_bot_mid':'lips_bot_ref.x',
                        'lips_bot':'lips_bot_ref',
                        'lips_bot_01': 'lips_bot_01_ref',
                        'lips_roll_top': 'lips_roll_top_ref.x',
                        'lips_roll_bot': 'lips_roll_bot_ref.x',   
                        'lips_offset': 'lips_offset_ref.x',
                        'muzzle': 'muzzle_ref.x',
                        'jaw':'jaw_ref.x' 
                        }
                        
mouth_bones_dict = {
                    'c_jawbone': {'name':'c_jawbone.x', 'deform':False, 'control':True},
                    'jawbone': {'name':'jawbone.x', 'deform':True, 'control':False},
                    'jawbone_track':{'name':'jawbone_track.x', 'deform':False, 'control':False},
                    'jaw_ret_bone': {'name':'jaw_ret_bone.x', 'deform':False, 'control':False},
                    
                    'c_lips_top_mid': {'name':'c_lips_top.x', 'deform':True, 'control':True},                   
                    'c_lips_top_retain_mid': {'name':'c_lips_top_retain.x', 'deform':False, 'control':False},
                    'c_lips_top_offset_mid': {'name':'c_lips_top_offset.x', 'deform':False, 'control':False},
                    
                    'c_lips_top': {'name':'c_lips_top', 'deform':True, 'control':True},
                    'c_lips_top_offset': {'name':'c_lips_top_offset', 'deform':False, 'control':False},
                    'c_lips_top_retain':{'name':'c_lips_top_retain', 'deform':False, 'control':False},
                    
                    'c_lips_top_01': {'name':'c_lips_top_01', 'deform':True, 'control':True},
                    'c_lips_top_01_offset': {'name':'c_lips_top_01_offset', 'deform':False, 'control':False},
                    'c_lips_top_01_retain': {'name':'c_lips_top_01_retain', 'deform':False, 'control':False},
                    
                    'c_lips_bot_mid': {'name':'c_lips_bot.x', 'deform':True, 'control':True},             
                    'c_lips_bot_offset_mid': {'name':'c_lips_bot_offset.x', 'deform':False, 'control':False},  
                    'c_lips_bot_retain_mid': {'name':'c_lips_bot_retain.x', 'deform':False, 'control':False},
                    
                    'c_lips_bot': {'name':'c_lips_bot', 'deform':True, 'control':True}, 
                    'c_lips_bot_offset': {'name':'c_lips_bot_offset', 'deform':False, 'control':False},
                    'c_lips_bot_retain': {'name':'c_lips_bot_retain', 'deform':False, 'control':False},
                    
                    'c_lips_bot_01': {'name':'c_lips_bot_01', 'deform':True, 'control':True},
                    'c_lips_bot_01_offset': {'name':'c_lips_bot_01_offset', 'deform':False, 'control':False},                 
                    'c_lips_bot_01_retain': {'name':'c_lips_bot_01_retain', 'deform':False, 'control':False},                    
                                          
                    'c_lips_smile': {'name':'c_lips_smile', 'deform':True, 'control':True},
                    'c_lips_smile_offset': {'name':'c_lips_smile_offset', 'deform':False, 'control':False},            
                    'c_lips_smile_retain': {'name':'c_lips_smile_retain', 'deform':False, 'control':False},
                    
                    'c_lips_corner_mini': {'name':'c_lips_corner_mini', 'deform':True, 'control':True},
                    'c_lips_corner_mini_offset': {'name':'c_lips_corner_mini_offset', 'deform':False, 'control':False},
                    'c_lips_corner_mini_retain': {'name':'c_lips_corner_mini_retain', 'deform':False, 'control':False},
                    
                    'c_lips_roll_bot': {'name':'c_lips_roll_bot.x', 'deform':False, 'control':True},
                    'c_lips_roll_top': {'name':'c_lips_roll_top.x', 'deform':False, 'control':True},
                    'c_lips_offset': {'name':'c_lips_offset.x', 'deform':False, 'control':True},
                    'c_muzzle': {'name':'c_muzzle.x', 'deform':False, 'control':True}
                    }
                    
                    
mouth_bones_base = [j['name'] for i, j in mouth_bones_dict.items()]
mouth_ref_base = [j for i, j in mouth_bones_ref_dict.items()]   

mouth_ref = []
mouth_bones = []
    
for i in mouth_bones_base:
    if i.endswith('.x'):
        mouth_bones.append(i)
    else:
        mouth_bones.append(i+'.l')
        mouth_bones.append(i+'.r')
        
for i in mouth_ref_base:
    if i.endswith('.x'):
        mouth_ref.append(i)
    else:
        mouth_ref.append(i+'.l')
        mouth_ref.append(i+'.r')

        
def get_variable_lips(head_side, btype='REFERENCE', no_side=False, levels=['top_', 'bot_']):
    types = [btype]    
    if btype == 'ALL':
        types = ['REFERENCE', 'CONTROLLER', 'CONT_MASTER', 'OFFSET', 'RETAIN', 'FOLLOW']
    if btype == 'NON_REF':
        types = ['CONTROLLER', 'CONT_MASTER', 'OFFSET', 'RETAIN', 'FOLLOW']
        
    lips_list = []

    for subtype in types:
        for lip_id in range(1, 32):
            for _side in ['.l', '.r']:
                for lvl in levels:
                    bname = ''
                    if subtype == 'REFERENCE':
                        bname = 'lips_' + lvl + '%02d' % lip_id + '_ref' + head_side[:-2] + _side
                    elif subtype == 'CONTROLLER':
                        bname = 'c_lips_' + lvl + '%02d' % lip_id + head_side[:-2] + _side   
                    elif subtype == 'CONT_MASTER':
                        bname = 'c_lips_' + lvl + '%02d' % lip_id + '_master' + head_side[:-2] + _side  
                        if lip_id == 1:                            
                            bname_0 = 'c_lips_' + lvl + 'master' + head_side[:-2] + '.x'                           
                            if bpy.context.active_object.data.bones.get(bname_0):                             
                                if not bname_0 in lips_list:# always append .x even if no_side
                                    lips_list.append(bname_0)                                    
                    elif subtype == 'OFFSET':
                        bname = 'c_lips_' + lvl + '%02d' % lip_id + '_offset' + head_side[:-2] + _side
                    elif subtype == 'RETAIN':
                        bname = 'c_lips_' + lvl + '%02d' % lip_id + '_retain' + head_side[:-2] + _side
                    elif subtype == 'FOLLOW':
                        bname = 'lips_' + lvl + '%02d' % lip_id + '_retain' + head_side[:-2] + _side
                    
                    if bpy.context.active_object.data.bones.get(bname):
                        if no_side:
                            bname = bname.replace(head_side[:-2]+_side, '')
                        lips_list.append(bname)
            
    return lips_list
    
    
def get_lip_idx(name):
    for i in name.split('_'):
        i = i.split('.')[0]
        if i.isdigit() and len(i) == 2:
            return int(i)    
    return 0# no string idx found, is zero
    
    

# cheeks
cheek_bones_ref_dict = {'cheek_smile': 'cheek_smile_ref',
                        'cheek_inflate': 'cheek_inflate_ref',
                        'cheek_push': 'cheek_push_ref',
                        'cheek_pole': 'cheek_pole_ref'}
cheek_bones_dict = {'cheek_smile':{'name':'c_cheek_smile', 'deform':True, 'control':True}, 
                    'cheek_inflate':{'name':'c_cheek_inflate', 'deform':True, 'control':True},                    
                    'cheek_push':{'name': 'cheek_push', 'deform':False, 'control':False},
                    'cheek_push_target':{'name': 'cheek_push_tar', 'deform':False, 'control':False},
                    'cheek_stretch':{'name': 'cheek_str', 'deform':False, 'control':False},                    
                    'cheek_inflate_offset':{'name': 'cheek_inflate_off', 'deform':False, 'control':False},
                    'cheek_smile_offset':{'name': 'cheek_smile_off', 'deform':False, 'control':False},
                    'cheek_pole': {'name': 'cheek_pole', 'deform': False, 'control': False}
                    }
                    
cheek_bones_base = [j['name'] for i, j in cheek_bones_dict.items()]
cheek_ref_base = [j for i, j in cheek_bones_ref_dict.items()]
    
cheek_bones = []
for i in cheek_bones_base:
    cheek_bones.append(i+'.l')
    cheek_bones.append(i+'.r')
    
cheek_ref = []
for i in cheek_ref_base:
    cheek_ref.append(i+'.l')
    cheek_ref.append(i+'.r')
    
    
#   chins
chin_bones_ref_dict = {'chin_01': 'chin_01_ref.x', 
                    'chin_02': 'chin_02_ref.x'}
              
chin_bones_dict = {'chin01': {'name':'c_chin_01.x', 'deform':True, 'control':True}, 
                'chin02': {'name':'c_chin_02.x', 'deform':True, 'control':True}
                }

chin_bones = [j['name'] for i, j in chin_bones_dict.items()]
chin_ref = [j for i, j in chin_bones_ref_dict.items()]
    
    
#   nose
nose_bones_ref_dict = {'nose_01': 'nose_01_ref.x',
                        'nose_02': 'nose_02_ref.x', 
                        'nose_03': 'nose_03_ref.x'}
                    
nose_bones_dict = {'nose_01': {'name':'c_nose_01.x', 'deform':True, 'control':True},
                'nose_02':{'name':'c_nose_02.x', 'deform':True, 'control':True},
                'nose_03': {'name':'c_nose_03.x', 'deform':True, 'control':True}
                }

nose_bones = [j['name'] for i, j in nose_bones_dict.items()]
nose_ref = [j for i, j in nose_bones_ref_dict.items()]
    
    
#   teeth
teeth_bones_ref_dict = {'teeth_top_mid': 'teeth_top_ref.x',
                        'teeth_top': 'teeth_top_ref',
                        'teeth_bot_mid': 'teeth_bot_ref.x',
                        'teeth_bot': 'teeth_bot_ref',
                        }
                        
teeth_bones_dict = {'teeth_top_master': {'name':'c_teeth_top_master.x', 'deform':False, 'control':True},
                    'c_teeth_top_mid': {'name':'c_teeth_top.x', 'deform':True, 'control':True},
                    'c_teeth_top': {'name':'c_teeth_top', 'deform':True, 'control':True},                    
                    'teeth_bot_master': {'name':'c_teeth_bot_master.x', 'deform':False, 'control':True},
                    'c_teeth_bot_mid': {'name':'c_teeth_bot.x', 'deform':True, 'control':True},
                    'c_teeth_bot': {'name':'c_teeth_bot', 'deform':True, 'control':True},
                    }

teeth_bones_base = [teeth_bones_dict[i]['name'] for i in teeth_bones_dict]
teeth_ref_base = [j for i, j in teeth_bones_ref_dict.items()]
teeth_bones_def_base = [teeth_bones_dict[i]['name'] for i in teeth_bones_dict if teeth_bones_dict[i]['deform']]

teeth_bones = []
for i in teeth_bones_base:
    if i.endswith('.x'):
        teeth_bones.append(i)
    else:
        teeth_bones.append(i+'.l')
        teeth_bones.append(i+'.r')
        
teeth_bones_def = []
for i in teeth_bones_def_base:
    if i.endswith('.x'):
        teeth_bones_def.append(i)
    else:
        teeth_bones_def.append(i+'.l')
        teeth_bones_def.append(i+'.r')
        
teeth_ref = []
for i in teeth_ref_base:
    if i.endswith('.x'):
        teeth_ref.append(i)
    else:
        teeth_ref.append(i+'.l')
        teeth_ref.append(i+'.r')
    
# tongues
tongue_bones_ref_dict = {'tong_01':'tong_01_ref.x',
                        'tong_02':'tong_02_ref.x',
                        'tong_03':'tong_03_ref.x'
                        }
                        
tongue_bones_dict = {'c_tong_01': {'name':'c_tong_01.x', 'deform':False, 'control':True},
                    'c_tong_02': {'name':'c_tong_02.x', 'deform':False, 'control':True},
                    'c_tong_03': {'name':'c_tong_03.x', 'deform':False, 'control':True},
                    'tong_01': {'name':'tong_01.x', 'deform':True, 'control':False},
                    'tong_02': {'name':'tong_02.x', 'deform':True, 'control':False},
                    'tong_03': {'name':'tong_03.x', 'deform':True, 'control':False}
                    }
                    
tongue_ref = [j for i, j in tongue_bones_ref_dict.items()]
tongue_bones = [tongue_bones_dict[i]['name'] for i in tongue_bones_dict]


def get_tongues(side='.x', type='ALL', no_side=True, side_x=False):
    list = []
    ctrl = []
    ref = []
    deform = []
    _side = '' if no_side else side
    _sidex = '.x' if side_x else ''
    for _i in range(1, 33):
        stri = '%02d' % _i
        if bpy.context.active_object.data.bones.get('tong_'+stri+'_ref'+side):
            ctrl.append('c_tong_'+stri+_side+_sidex)
            ref.append('tong_'+stri+'_ref'+_side+_sidex)
            deform.append('tong_'+stri+_side+_sidex)
            
    if type == 'ALL':
        list = ctrl + ref + deform
    elif type == 'CTRL':
        list = ctrl
    elif type == 'REF':
        list = ref
    elif type == 'DEF':
        list = deform
    elif type == 'NON_REF':
        list = ctrl + deform
    
    return list
    
    
# eyes
eye_bones_ref_dict = {'eye_offset': 'eye_offset_ref',
                    'eyelod_top': 'eyelid_top_ref',
                    'eyelid_twk_top': 'eyelid_twk_top_ref',
                    'eyelid_bot': 'eyelid_bot_ref',
                    'eyelid_twk_bot': 'eyelid_twk_bot_ref',
                    'eyelid_top_01': 'eyelid_top_01_ref',
                    'eyelid_bot_01': 'eyelid_bot_01_ref',
                    'eyelid_corner_01': 'eyelid_corner_01_ref',
                    'eyelid_corner_02': 'eyelid_corner_02_ref',
                    }
                    
                    
eye_bones_dict = {
                   'eye_ref_track': {'name':'c_eye_ref_track', 'deform':True, 'control':False},
                   'eye_offset': {'name':'c_eye_offset', 'deform':True, 'control':True},
                   'eyelid_base_top': {'name':'eyelid_base_top', 'deform':False, 'control':False},
                   'eyelid_base_bot': {'name':'eyelid_base_bot', 'deform':False, 'control':False},
                   'eyelid_top': {'name':'eyelid_top', 'deform':False, 'control':False},
                   'eyelid_top_01': {'name':'c_eyelid_top_01', 'deform':True, 'control':True}, 
                   'eyelid_twk_top': {'name': 'c_eyelid_twk_top', 'deform':True, 'control':True},  
                   'eyelid_bot': {'name': 'eyelid_bot', 'deform':False, 'control':False},
                   'eyelid_bot_01': {'name': 'c_eyelid_bot_01', 'deform':True, 'control':True},
                   'eyelid_twk_bot': {'name': 'c_eyelid_twk_bot', 'deform':True, 'control':True},   
                   'c_eye':  {'name': 'c_eye', 'deform':True, 'control':True},
                   'c_eye_ref': {'name': 'c_eye_ref', 'deform':False, 'control':True},
                   'eyelid_corner_01' : {'name': 'c_eyelid_corner_01', 'deform':True, 'control':True},
                   'eyelid_corner_02': {'name': 'c_eyelid_corner_02', 'deform':True, 'control':True},
                   'c_eyelid_top': {'name': 'c_eyelid_top', 'deform':False, 'control':True},
                   'c_eyelid_bot': {'name': 'c_eyelid_bot', 'deform':False, 'control':True},
                   'c_eye_target': {'name': 'c_eye_target', 'deform':False, 'control':True},
                   'c_eye_target_mid': {'name': 'c_eye_target.x', 'deform':False, 'control':True}
                   }
                    
                    
eyelids_bones_ref_default_dict = {'eyelid_top_02': 'eyelid_top_02_ref',
                            'eyelid_top_03': 'eyelid_top_03_ref',
                            'eyelid_bot_02': 'eyelid_bot_02_ref',
                            'eyelid_bot_03': 'eyelid_bot_03_ref'}
                            
                    
def get_eyelid_idx(name):
    for i in name.split('_'):
        i = i.split('.')[0]
        if i.isdigit() and len(i) == 2:
            return int(i)    
    return 0# no string idx found, is zero
    
                    
def get_variable_eyelids(head_side, eye_sides=['.l', '.r'], btype='REFERENCE', levels=['top_', 'bot_'], no_side=False):
    types = [btype]    
    if btype == 'ALL':
        types = ['REFERENCE', 'CONTROLLER', 'CONT_MASTER', 'OFFSET']
   
    eyelids_list = []

    for subtype in types:
        for eyel_id in range(1,32):
            str_i = '%02d' % eyel_id
            for _side in eye_sides:
                for lvl in levels:
                    bname = ''
                    if subtype == 'REFERENCE':
                        bname = 'eyelid_'+lvl+str_i+'_ref'+head_side[:-2]+_side
                    elif subtype == 'CONTROLLER':
                        bname = 'c_eyelid_' + lvl + str_i + head_side[:-2] + _side
                    elif subtype == 'CONT_MASTER':
                        bname = 'c_eyelid_'+lvl+str_i+'_master'+head_side[:-2]+_side
                    elif subtype == 'OFFSET':
                        bname = 'eyelid_'+lvl+str_i+'_offset'+head_side[:-2]+_side
                    
                    if bpy.context.active_object.data.bones.get(bname):
                        if no_side:
                            bname = bname.replace(head_side[:-2]+_side, '')
                        eyelids_list.append(bname)
            
    return eyelids_list
    

eye_bones = [j['name'] for i, j in eye_bones_dict.items()] 
eye_ref = [j for i, j in eye_bones_ref_dict.items()] 
eyelids_default_ref = [j for i, j in eyelids_bones_ref_default_dict.items()]

eye_bones_mid = ['c_eye_target.x']
eye_bones_left = [i+'.l' for i in eye_bones] + [i+'.l' for i in eye_ref] + [i+'.l' for i in eyelids_default_ref]
eye_bones_right = [i+'.r' for i in eye_bones] + [i+'.r' for i in eye_ref] + [i+'.r' for i in eyelids_default_ref]


# eyebrows
eyebrow_bones_ref_dict = {'eyebrow_full': 'eyebrow_full_ref', 
                        'eyebrow_03': 'eyebrow_03_ref', 
                        'eyebrow_02': 'eyebrow_02_ref', 
                        'eyebrow_01': 'eyebrow_01_ref', 
                        'eyebrow_01_end': 'eyebrow_01_end_ref'
                        }
                        
eyebrow_mid_bones_ref_dict = {'eyebrow_mid': 'eyebrow_mid_ref.x'}

eyebrow_bones_dict = {
                    'eyebrow_full': {'name':'c_eyebrow_full', 'deform':False, 'control':True},
                    'eyebrow_03': {'name':'c_eyebrow_03', 'deform':True, 'control':True},
                    'eyebrow_02': {'name':'c_eyebrow_02', 'deform':True, 'control':True},
                    'eyebrow_01': {'name':'c_eyebrow_01', 'deform':True, 'control':True},
                    'eyebrow_01_end': {'name':'c_eyebrow_01_end', 'deform':True, 'control':True}
                    }
                    
eyebrow_mid_bones_dict = {
                        'eyebrow_mid': {'name': 'c_eyebrow_mid.x', 'deform':True, 'control':True},
                        'eyebrow_mid_str': {'name': 'eyebrow_str.x', 'deform':False, 'control':False},
                        'eyebrow_str_pos': {'name': 'eyebrow_str_pos.x', 'deform':False, 'control':False},
                        'eyebrow_str_pos_off': {'name': 'eyebrow_str_pos_off.x', 'deform':False, 'control':False}
                        }
                        
eyebrow_bones = [j['name'] for i, j in eyebrow_bones_dict.items()]
eyebrow_bones_mid = [j['name'] for i, j in eyebrow_mid_bones_dict.items()]
eyebrow_ref = [j for i, j in eyebrow_bones_ref_dict.items()]
eyebrow_ref_mid = [j for i, j in eyebrow_mid_bones_ref_dict.items()]
    
eyebrow_bones_left = [i+'.l' for i in eyebrow_bones] + [i+'.l' for i in eyebrow_ref]
eyebrow_bones_right = [i+'.r' for i in eyebrow_bones] + [i+'.r' for i in eyebrow_ref]


def get_eyebrows(side='.l', type='ALL', include_full=True, include_mid=False, with_side=False, with_side_x_only=False):
    list = []
    main_ctrl = []
    ref = []    
    
    if side.endswith('.x'): 
        side = side[:-2]+'.l'# same count for left and right brows for now    
    
    side_suff = '' if with_side == False else side
    side_suff_x = '' 
    if with_side or with_side_x_only:
        side_suff_x = '.x'
    
    for _i in range(0, 32):
        stri = '%02d' % _i if _i > 0 else '01_end'
        if bpy.context.active_object.data.bones.get('eyebrow_'+stri+'_ref'+side):
            ref.append('eyebrow_'+stri+'_ref'+side_suff)
            main_ctrl.append('c_eyebrow_'+stri+side_suff)

    if include_mid:
        eyebrow_mid_ref_name = 'eyebrow_mid_ref'+side[:-2]+'.x'
        c_eyebrow_mid_name = 'c_eyebrow_mid'+side[:-2]+'.x'
        if bpy.context.active_object.data.bones.get(eyebrow_mid_ref_name):
            ref.append('eyebrow_mid_ref'+side_suff_x)
            main_ctrl.append('c_eyebrow_mid'+side_suff_x)  
    
    
    master_ctrl = [eyebrow_bones_dict['eyebrow_full']['name']+side_suff]
    master_ref = [eyebrow_bones_ref_dict['eyebrow_full']+side_suff]
    
    if type == 'ALL':
        list = main_ctrl + ref
        if include_full:
            list += master_ctrl + master_ref
    elif type == 'CTRL':
        list = main_ctrl
        if include_full:
            list += master_ctrl
    elif type == 'REF':
        list = ref
        if include_full:
            list += master_ref
    
    return list


#   facial
facial_ref_dict = {}            
facial_ref_dict.update(mouth_bones_ref_dict)
facial_ref_dict.update(cheek_bones_ref_dict)
facial_ref_dict.update(chin_bones_ref_dict)
facial_ref_dict.update(nose_bones_ref_dict)
facial_ref_dict.update(eye_bones_ref_dict)
facial_ref_dict.update(eyebrow_bones_ref_dict)
facial_ref_dict.update(eyebrow_mid_bones_ref_dict)
facial_ref_dict.update(teeth_bones_ref_dict)
facial_ref_dict.update(tongue_bones_ref_dict)

facial_ref = [j for i, j in facial_ref_dict.items()]

mouth_deform = [mouth_bones_dict[i]['name'] for i in mouth_bones_dict if mouth_bones_dict[i]['deform']] 
cheek_deform = [cheek_bones_dict[i]['name'] for i in cheek_bones_dict if cheek_bones_dict[i]['deform']]
chin_deform = [chin_bones_dict[i]['name'] for i in chin_bones_dict if chin_bones_dict[i]['deform']]
nose_deform = [nose_bones_dict[i]['name'] for i in nose_bones_dict if nose_bones_dict[i]['deform']]
eye_deform = [eye_bones_dict[i]['name'] for i in eye_bones_dict if eye_bones_dict[i]['deform']]
eyebrow_deform = [eyebrow_bones_dict[i]['name'] for i in eyebrow_bones_dict if eyebrow_bones_dict[i]['deform']]
teeth_deform = [teeth_bones_dict[i]['name'] for i in teeth_bones_dict if teeth_bones_dict[i]['deform']]
tongue_deform = [tongue_bones_dict[i]['name'] for i in tongue_bones_dict if tongue_bones_dict[i]['deform']]

facial_deform = mouth_deform + cheek_deform + chin_deform + nose_deform + eye_deform + eyebrow_deform + teeth_deform + tongue_deform

mouth_control = [mouth_bones_dict[i]['name'] for i in mouth_bones_dict if mouth_bones_dict[i]['control']]
cheek_control = [cheek_bones_dict[i]['name'] for i in cheek_bones_dict if cheek_bones_dict[i]['control']]
chin_control = [chin_bones_dict[i]['name'] for i in chin_bones_dict if chin_bones_dict[i]['control']]
nose_control = [nose_bones_dict[i]['name'] for i in nose_bones_dict if nose_bones_dict[i]['control']]
eye_control = [eye_bones_dict[i]['name'] for i in eye_bones_dict if eye_bones_dict[i]['control']]
eyebrow_control = [eyebrow_bones_dict[i]['name'] for i in eyebrow_bones_dict if eyebrow_bones_dict[i]['control']]
teeth_control = [teeth_bones_dict[i]['name'] for i in teeth_bones_dict if teeth_bones_dict[i]['control']]
tongue_control = [tongue_bones_dict[i]['name'] for i in tongue_bones_dict if tongue_bones_dict[i]['control']]

facial_control = mouth_control + cheek_control + chin_control + nose_control + eye_control + eyebrow_control + teeth_control + tongue_control

facial_bones = eyebrow_bones + eyebrow_bones_mid + eye_bones_mid + eye_bones + nose_bones + chin_bones + cheek_bones_base + mouth_bones_base + teeth_bones_base + tongue_bones

# EARS
ear_ref = ['ear_01_ref', 'ear_02_ref']
ear_control = ['c_ear_01', 'c_ear_02']

def get_ears_controllers(side):
    ears_list = []
    for ear_id in range(0,17):
        ear_n = 'ear_' + '%02d' % ear_id + '_ref' + side
        if bpy.context.active_object.data.bones.get(ear_n):
            ears_list.append('c_ear_' + '%02d' % ear_id + side)
    return ears_list



# NECK
neck_bones_dict = {
                    'control': 'c_neck.x',
                    'control_01': 'c_neck_01.x',
                    'deform': 'neck.x',
                    'c_p': 'c_p_neck.x',
                    'c_p_01': 'c_p_neck_01.x',
                    'twist': 'neck_twist.x',
                    'twist_target': 'neck_twist_tar.x',
                    }
                    
neck_ref_dict = {'neck': 'neck_ref.x'}                    
neck_deform = [neck_bones_dict['control_01'], neck_bones_dict['deform']]
neck_control = [neck_bones_dict['control'], neck_bones_dict['control_01']]
neck_bones = [j for i, j in neck_bones_dict.items()]
neck_ref = [neck_ref_dict['neck']]

subnecks = ['subneck_']



# SPINE
def get_spine_name(type, idx):
    # get spine bone name by type
    # only supports a single side for now, .x
    _s = '.x'
    str_idx = '%02d' % idx    
    
    if type == 'ref':
        return'spine_'+str_idx+'_ref'+_s
        
    elif type == 'control':
        return 'c_spine_'+str_idx+_s
        
    elif type == 'control_bend':
        return 'c_spine_'+str_idx+'_bend'+_s
        
    elif type == 'base':
        return 'spine_'+str_idx+_s  
        
    elif type == 'shape_override':
        return 'c_p_spine_'+str_idx+_s
        
    elif type == 'control_proxy':
        return 'c_spine_'+str_idx+'_proxy'+_s
        
    elif type == 'control_bend_proxy':
        return 'c_spine_'+str_idx+'_bend_proxy'+_s
        
    elif type == 'control_reverse':
        if idx == 0:
            return spine_bones_dict['c_root_rev']
        else:
            return 'c_spine_'+str_idx+'_rev'+_s
        
    elif type == 'control_reverse_proxy':
        if idx == 0:
            return 'c_root_rev_proxy'+_s
        else:
            return 'c_spine_'+str_idx+'_rev_proxy'+_s
        
    
    
        
        
def get_spine_idx(name, type='int'):    
    for i in name.split('_'):
        i = i.split('.')[0]# remove side chars
        if i.isdigit() and len(i) == 2: 
            if type == 'int':
                return int(i)
            elif type == 'string':
                return i
    return None
        

spine_bones_dict = {
    'c_root_master': 'c_root_master.x', 'c_root':'c_root.x', 'root':'root.x', 'c_root_bend':'c_root_bend.x', 
    'c_root_rev':'c_root_rev.x',
    'c_waist_bend':'c_waist_bend.x', 'root_master_shape_override':'c_p_root_master.x', 'root_shape_override':'c_p_root.x', 
    'spine_01_shape_override':get_spine_name('shape_override', 1), 'spine_02_shape_override':get_spine_name('shape_override', 2), 
    'c_spine_01':get_spine_name('control', 1), 'spine_01':get_spine_name('base', 1), 'c_spine_01_bend':get_spine_name('control_bend', 1), 'spine_01_cns': 'spine_01_cns.x', 
    'c_spine_02':get_spine_name('control', 2), 'spine_02':get_spine_name('base', 2), 'c_spine_02_bend':get_spine_name('control_bend', 2), 'spine_02_cns': 'spine_02_cns.x',
    'c_spine_master': 'c_spine_master.x', 'stretchy': 'spine_stretchy.x',
    'c_spine_master_rev': 'c_spine_master_rev.x', 'stretchy_rev': 'spine_stretchy_rev.x'}

spine_bones = [j for i, j in spine_bones_dict.items()]

spine_03_intern = ['spine_03_cns.x']
spine03_deform = [get_spine_name('base', 3)]
spine03_control = [get_spine_name('control', 3), get_spine_name('control_proxy', 3), get_spine_name('control_bend', 3)]

spine02_deform = [spine_bones_dict['c_spine_02_bend'], spine_bones_dict['spine_02']]
spine02_control = [spine_bones_dict['c_spine_02'], spine_bones_dict['c_spine_02_bend'], get_spine_name('control_proxy', 2), get_spine_name('control_bend_proxy', 2)]

spine01_deform = [spine_bones_dict['c_spine_01_bend'], spine_bones_dict['spine_01']]

spine01_control = [spine_bones_dict['c_spine_01'], spine_bones_dict['c_spine_01_bend'], get_spine_name('control_proxy', 1), get_spine_name('control_bend_proxy', 1)]

spine_ref_dict = {'root':'root_ref.x', 'spine_01':get_spine_name('ref', 1), 'spine_02': get_spine_name('ref', 2)}

bot_ref_dict = {'bot': 'bot_bend_ref'}

bot_dict = {'c_bot': 'c_bot_bend'}

spine_ref_list = [j for i, j in spine_ref_dict.items()]

spine_bones_rig_add = [spine_bones_dict['c_waist_bend'], 'c_waist_bend_end.x', 'epaules_bend.x']

spine_control = spine01_control + spine02_control + [spine_bones_dict['c_root'], spine_bones_dict['c_root_master'], spine_bones_dict['c_root_bend']]


# Breast
breast_ref_dict = {
                    '01':'breast_01_ref',
                    '02':'breast_02_ref'
                }
                
breast_bones_dict = {
                    '01':'c_breast_01',
                    '02':'c_breast_02',
                }
                
breast_bones = [j for i, j in breast_bones_dict.items()]


# SPLINE IK
spline_ik_bones = ['c_spline_root', 'spline_stretch', 'c_spline_curvy', 'c_spline_tip']

def get_spline_ik(rig, side):
    for ch in rig.children:
        if ch.type == 'CURVE' and ch.name.startswith('spline_ik_curve'+side):
            return ch
    return None



#SMART FACIAL MARKERS
facial_markers = {
'eyebrow_01_end.l': 15, 'eyebrow_01.l':16, 'eyebrow_02.l':17, 'eyebrow_03.l':18, 
'eyebrow_01_end.r':40, 'eyebrow_01.r':41, 'eyebrow_02.r':42, 'eyebrow_03.r':43,
'eyelid_corner_01.l':7, 'eyelid_bot_01.l':6, 'eyelid_bot_02.l':5, 'eyelid_bot_03.l':12, 'eyelid_corner_02.l':11, 'eyelid_top_03.l':10, 'eyelid_top_02.l':9, 'eyelid_top_01.l':8, 'eyelid_corner_01.r':30, 'eyelid_bot_01.r':29, 'eyelid_bot_02.r':28, 'eyelid_bot_03.r':35, 'eyelid_corner_02.r':34, 'eyelid_top_03.r':33, 'eyelid_top_02.r':32, 'eyelid_top_01.r':31,
'nose_03.x':36, 'nose_01.x':37, 
'cheek_smile.l':13, 'cheek_inflate.l':14, 'cheek_smile.r':38, 'cheek_inflate.r':39, 
'lips_top.x':22, 'lips_top.l':0, 'lips_top_01.l':1, 'lips_smile.l':2, 'lips_bot_01.l':3, 'lips_bot.l':4, 'lips_bot.x':21, 'lips_top.r':23, 'lips_top_01.r':24, 'lips_smile.r':25, 'lips_bot_01.r':26, 'lips_bot.r':27,
'chin_01.x': 47, 'chin_02.x':46, 
'ear_01.l':20, 'ear_02.l':19, 'ear_01.r':45, 'ear_02.r':44}



#UPDATE
bones_arp_layer = {'c_eyebrow_01_proxy.l': 0, 'c_index2.l': 0, 'c_index1_base.r': 0, 'c_eyelid_bot_01_proxy.l': 1, 'c_neck_thick_proxy.x': 1, 'c_pinky1.l': 0, 'c_eyebrow_03_proxy.l': 0, 'c_foot_01_proxy.l': 0, 'c_eyelid_bot_03.l': 1, 'c_spine_01_proxy.x': 0, 'c_breast_01_proxy.r': 1, 'c_thumb1.l': 0, 'c_eyebrow_03.l': 0, 'c_eyelid_top_03_proxy.r': 1, 'c_pinky2.l': 0, 'c_eyelid_corner_02_proxy.l': 1, 'c_toes_ring2_proxy.l': 0, 'c_leg_bend_02_proxy.r': 1, 'c_toes_fk.l': 0, 'c_cheek_inflate.r': 1, 'c_toes_index3_proxy.r': 0, 'c_hand_ik_proxy.r': 0, 'c_thigh_bend_contact.r': 1, 'c_thigh_bend_contact.l': 1, 'c_eye_ref.l': 1, 'c_eyelid_top_03.l': 1, 'c_eyebrow_01_end_proxy.r': 0, 'c_lips_roll_bot_proxy.x': 0, 'c_toes_ring3_proxy.r': 0, 'c_eyebrow_full_proxy.l': 0, 'c_chin_02.x': 1, 'c_nose_02.x': 1, 'c_foot_01.l': 0, 'c_toes_ring3.r': 0, 'c_ring3.l': 0, 'c_ring2_proxy.r': 0, 'c_skull_01_proxy.x': 1, 'c_toes_pinky3_proxy.r': 0, 'c_toes_thumb1_proxy.l': 0, 'c_cheek_smile_proxy.l': 1, 'c_pinky1_base_proxy.r': 0, 'c_index1.l': 0, 'c_thigh_bend_02_proxy.r': 1, 'c_chin_02_proxy.x': 1, 'c_toes_pinky2_proxy.r': 0, 'c_foot_01_proxy.r': 0, 'c_lips_bot_01_proxy.r': 0, 'c_waist_bend.x': 1, 'c_eyebrow_02.l': 0, 'c_cheek_smile.l': 1, 'c_toes_middle3_proxy.l': 0, 'c_eyelid_bot_02_proxy.l': 1, 'c_breast_01_proxy.l': 1, 'c_toes_pinky3.l': 0, 'c_toes_middle3_proxy.r': 0, 'c_toes_index2.r': 0, 'c_index3_proxy.r': 0, 'c_skull_03_proxy.x': 1, 'c_neck.x': 0, 'c_head_proxy.x': 0, 'c_index1_proxy.r': 0, 'c_ring3_proxy.r': 0, 'c_tong_02_proxy.x': 0, 'c_toes_pinky1_proxy.l': 0, 'c_ring1_base_proxy.r': 0, 'c_index1_base_proxy.r': 0, 'c_eyebrow_full.l': 0, 'c_toes_thumb2_proxy.r': 0, 'c_root.x': 0, 'c_eyelid_corner_01.r': 1, 'c_cheek_smile.r': 1, 'c_eyelid_bot_01.l': 1, 'c_middle3_proxy.r': 0, 'c_teeth_top_proxy.x': 0, 'c_toes_index1_proxy.r': 0, 'c_skull_02_proxy.x': 1, 'c_thumb1_base.r': 0, 'c_thigh_bend_02_proxy.l': 1, 'c_lips_top_01_proxy.l': 0, 'c_lips_bot.x': 0, 'c_eyelid_bot_02.r': 1, 'c_arm_twist_offset.l': 0, 'c_lips_smile.l': 0, 'c_stretch_leg_proxy.r': 1, 'c_toes_ring3.l': 0, 'c_morph_jaw_round': 16, 'c_eye_offset.l': 1, 'c_lips_smile_proxy.l': 0, 'c_tong_01.x': 0, 'c_eye_ref.r': 1, 'c_thigh_bend_contact_proxy.r': 1, 'c_toes_ring2.r': 0, 'c_leg_bend_01.r': 1, 'c_thigh_fk_proxy.r': 0, 'c_eyebrow_01_end.r': 0, 'c_hand_ik_proxy.l': 0, 'c_traj_proxy': 0, 'c_pinky2.r': 0, 'c_elbow_bend.l': 1, 'c_lips_bot_proxy.l': 0, 'c_shoulder_bend.l': 1, 'c_shoulder_proxy.r': 0, 'c_foot_ik.l': 0, 'c_eyelid_bot_01.r': 1, 'c_leg_pole_proxy.l': 0, 'c_skull_02.x': 1, 'c_ankle_bend.r': 1, 'c_eyelid_corner_01_proxy.l': 1, 'c_middle3.r': 0, 'c_foot_fk.r': 0, 'c_eyelid_bot_proxy.r': 0, 'c_morph_mouth': 16, 'c_leg_bend_02.r': 1, 'c_eyelid_top.l': 0, 'c_thigh_bend_02.r': 1, 'c_hand_fk.r': 0, 'c_hand_fk_proxy.r': 0, 'c_pos_proxy': 0, 'c_leg_bend_01_proxy.l': 1, 'c_eye_offset_proxy.r': 1, 'c_arms_pole_proxy.l': 0, 'c_thigh_fk.r': 0, 'c_eyelid_top_03.r': 1, 'c_stretch_leg_pin_proxy.l': 1, 'c_lips_roll_bot.x': 0, 'c_ring1.r': 0, 'c_ring1.l': 0, 'c_thumb2.r': 0, 'c_forearm_bend_proxy.l': 1, 'c_lips_top_proxy.x': 0, 'c_index2_proxy.r': 0, 'c_toes_pinky3_proxy.l': 0, 'c_thigh_bend_01_proxy.r': 1, 'c_root_master.x': 0, 'c_nose_01_proxy.x': 1, 'c_skull_03.x': 1, 'c_thumb2_proxy.r': 0, 'c_arm_fk.l': 0, 'c_toes_thumb2.r': 0, 'c_jawbone_proxy.x': 0, 'c_spine_01_bend.x': 1, 'c_eyelid_top_proxy.r': 0, 'c_index3.r': 0, 'c_middle3_proxy.l': 0, 'c_arm_fk_proxy.r': 0, 'c_eyelid_bot_02_proxy.r': 1, 'c_tail_03_proxy.x': 0, 'c_middle1_proxy.l': 0, 'c_foot_fk_proxy.r': 0, 'c_lips_bot_01_proxy.l': 0, 'c_eye_target.r': 0, 'c_toes_thumb2.l': 0, 'c_toes_index3_proxy.l': 0, 'c_thumb1_base_proxy.l': 0, 'c_thigh_b_proxy.l': 1, 'c_leg_fk.l': 0, 'c_thigh_bend_01.r': 1, 'c_jawbone.x': 0, 'c_thigh_b.r': 1, 'c_toes_thumb1.r': 0, 'c_skull_01.x': 1, 'c_toes_index3.r': 0, 'c_toes_middle2_proxy.r': 0, 'c_middle1.l': 0, 'c_toes_fk_proxy.r': 0, 'c_lips_top.x': 0, 'c_shoulder.l': 0, 'c_index2_proxy.l': 0, 'c_toes_thumb1_proxy.r': 0, 'c_index3_proxy.l': 0, 'c_eye_proxy.r': 0, 'c_eye_offset.r': 1, 'c_middle1_base.l': 0, 'c_stretch_arm.r': 1, 'c_index1_base_proxy.l': 0, 'c_toes_index3.l': 0, 'c_nose_01.x': 1, 'c_eye_target_proxy.x': 0, 'c_neck_01.x': 1, 'c_middle2_proxy.r': 0, 'c_eyelid_top_02.r': 1, 'c_toes_index2_proxy.l': 0, 'c_arms_pole.r': 0, 'c_toes_ik.r': 0, 'c_pinky2_proxy.l': 0, 'c_lips_smile_proxy.r': 0, 'c_pinky3_proxy.r': 0, 'c_morph_eyelashes_size': 16, 'c_pinky2_proxy.r': 0, 'c_tail_02_proxy.x': 0, 'c_ring3.r': 0, 'c_eyebrow_02_proxy.l': 0, 'c_toes_fk.r': 0, 'c_thumb1.r': 0, 'c_toes_index1_proxy.l': 0, 'c_eyelid_bot_02.l': 1, 'c_wrist_bend.r': 1, 'c_foot_roll_cursor.r': 0, 'c_arm_bend_proxy.r': 1, 'c_toes_ring2.l': 0, 'c_pinky1_proxy.l': 0, 'c_toes_ring1.l': 0, 'c_toes_middle2.l': 0, 'c_stretch_leg_pin.r': 1, 'c_toes_middle1.l': 0, 'c_pinky3.r': 0, 'c_toes_index1.l': 0, 'c_eye_target_proxy.l': 0, 'c_lips_top_proxy.r': 0, 'c_knee_bend_proxy.r': 1, 'c_spine_01.x': 0, 'c_breast_02_proxy.r': 1, 'c_leg_pole.l': 0, 'c_nose_03_proxy.x': 1, 'c_lips_smile.r': 0, 'c_eye.l': 0, 'c_bot_bend.l': 1, 'c_stretch_arm_pin_proxy.l': 1, 'c_tong_03.x': 0, 'c_toes_middle3.l': 0, 'c_eyelid_bot.l': 0, 'c_toes_ik.l': 0, 'c_knee_bend.l': 1, 'c_ankle_bend_proxy.r': 1, 'c_eye_ref_proxy.r': 0, 'c_index1_proxy.l': 0, 'c_shoulder.r': 0, 'c_leg_fk.r': 0, 'c_pinky1.r': 0, 'c_toes_thumb2_proxy.l': 0, 'c_cheek_smile_proxy.r': 1, 'c_tong_02.x': 0, 'c_lips_top.r': 0, 'c_shoulder_bend.r': 1, 'c_lips_bot.r': 0, 'c_spine_02_bend_proxy.x': 1, 'c_wrist_bend.l': 1, 'c_spine_02.x': 0, 'c_ring1_proxy.l': 0, 'c_thumb1_base.l': 0, 'c_leg_pole_proxy.r': 0, 'c_lips_bot_01.l': 0, 'c_thigh_bend_01.l': 1, 'c_eyelid_top_01_proxy.r': 1, 'c_thumb3_proxy.r': 0, 'c_forearm_fk_proxy.r': 0, 'c_thigh_fk_proxy.l': 0, 'c_lips_bot_proxy.x': 0, 'c_thumb3.l': 0, 'c_eyelid_top.r': 0, 'c_eyelid_bot_01_proxy.r': 1, 'c_cheek_inflate.l': 1, 'c_elbow_bend_proxy.l': 1, 'c_stretch_leg_pin_proxy.r': 1, 'c_toes_middle1_proxy.r': 0, 'c_thigh_bend_02.l': 1, 'c_foot_roll_cursor_proxy.r': 0, 'c_hand_fk.l': 0, 'c_lips_top_01.l': 0, 'c_forearm_bend.r': 1, 'c_foot_ik_proxy.r': 0, 'c_thumb2_proxy.l': 0, 'c_eyebrow_01_end_proxy.l': 0, 'c_toes_middle2_proxy.l': 0, 'c_cheek_inflate_proxy.l': 1, 'c_nose_03.x': 1, 'c_tail_01_proxy.x': 0, 'c_eyelid_top_03_proxy.l': 1, 'c_stretch_arm_pin.r': 1, 'c_middle1.r': 0, 'c_arm_fk.r': 0, 'c_eyelid_corner_01.l': 1, 'c_teeth_bot.x': 0, 'c_toes_thumb1.l': 0, 'c_ring1_proxy.r': 0, 'c_leg_bend_01.l': 1, 'c_eyebrow_02.r': 0, 'c_arms_pole.l': 0, 'c_toes_index2.l': 0, 'c_pinky1_base.l': 0, 'c_root_proxy.x': 0, 'c_toes_ik_proxy.l': 0, 'c_eye_ref_proxy.l': 0, 'c_ring1_base.l': 0, 'c_ring1_base.r': 0, 'c_leg_bend_02.l': 1, 'c_eyelid_corner_02.l': 1, 'c_eyelid_bot_03_proxy.r': 1, 'c_toes_ik_proxy.r': 0, 'c_thigh_b_proxy.r': 1, 'c_arm_bend_proxy.l': 1, 'c_eyebrow_03_proxy.r': 0, 'c_toes_index2_proxy.r': 0, 'c_arm_twist_offset_proxy.r': 0, 'c_thigh_bend_contact_proxy.l': 1, 'c_toes_middle3.r': 0, 'c_toes_ring1.r': 0, 'c_shoulder_proxy.l': 0, 'c_foot_roll_cursor_proxy.l': 0, 'c_leg_pole.r': 0, 'c_eyebrow_01_end.l': 0, 'c_eyelid_corner_02.r': 1, 'c_stretch_leg.r': 1, 'c_lips_corner_mini.r': 0, 'c_lips_roll_top.x': 0, 'c_eyelid_top_02_proxy.l': 1, 'c_cheek_inflate_proxy.r': 1, 'c_breast_02_proxy.l': 1, 'c_teeth_top.x': 0, 'c_leg_fk_proxy.l': 0, 'c_eyelid_top_proxy.l': 0, 'c_forearm_fk.r': 0, 'c_teeth_bot_proxy.x': 0, 'c_toes_ring1_proxy.r': 0, 'c_iris.r': 16, 'c_toes_pinky2.r': 0, 'c_middle1_base.r': 0, 'c_eye_target_proxy.r': 0, 'c_index1.r': 0, 'c_eyelid_bot_03.r': 1, 'c_tong_01_proxy.x': 0, 'c_pinky1_base_proxy.l': 0, 'c_middle1_proxy.r': 0, 'c_chin_01.x': 1, 'c_index2.r': 0, 'c_arms_pole_proxy.r': 0, 'c_root_master_proxy.x': 0, 'c_eyelid_top_01.r': 1, 'c_eyebrow_01_proxy.r': 0, 'c_middle1_base_proxy.r': 0, 'c_bot_bend_proxy.l': 1, 'c_pinky3_proxy.l': 0, 'layer_disp_second': 16, 'c_bot_bend.r': 1, 'c_index3.l': 0, 'c_toes_middle2.r': 0, 'c_elbow_bend.r': 1, 'c_lips_corner_mini_proxy.l': 0, 'c_lips_top_01_proxy.r': 0, 'c_thumb2.l': 0, 'c_toes_fk_proxy.l': 0, 'c_waist_bend_proxy.x': 1, 'c_middle1_base_proxy.l': 0, 'c_pinky3.l': 0, 'c_pupil.r': 16, 'c_eyelid_bot_03_proxy.l': 1, 'layer_disp_hair_long.001': 16, 'c_eyebrow_full_proxy.r': 0, 'c_eyelid_top_02_proxy.r': 1, 'c_eyebrow_01.r': 0, 'c_toes_index1.r': 0, 'c_middle2.l': 0, 'c_thigh_fk.l': 0, 'c_forearm_bend.l': 1, 'c_eyelid_top_02.l': 1, 'c_neck_proxy.x': 0, 'c_ring2.r': 0, 'c_ring3_proxy.l': 0, 'c_eyebrow_03.r': 0, 'c_lips_corner_mini_proxy.r': 0, 'c_nose_02_proxy.x': 1, 'c_foot_01.r': 0, 'c_thumb3.r': 0, 'c_toes_pinky2_proxy.l': 0, 'c_toes_ring2_proxy.r': 0, 'c_eyelid_bot_proxy.l': 0, 'c_knee_bend.r': 1, 'c_toes_pinky1.r': 0, 'c_shoulder_bend_proxy.r': 1, 'c_middle2.r': 0, 'c_toes_pinky1.l': 0, 'c_chin_01_proxy.x': 1, 'c_ring2_proxy.l': 0, 'c_spine_02_bend.x': 1, 'c_traj': 0, 'c_thumb3_proxy.l': 0, 'c_thumb1_proxy.l': 0, 'c_eyelid_top_01_proxy.l': 1, 'c_arm_fk_proxy.l': 0, 'c_arm_bend.r': 1, 'c_eye_target.l': 0, 'c_forearm_fk_proxy.l': 0, 'c_arm_twist_offset_proxy.l': 0, 'c_toes_ring1_proxy.l': 0, 'c_hand_fk_proxy.l': 0, 'c_pinky1_base.r': 0, 'c_eyelid_bot.r': 0, 'c_forearm_fk.l': 0, 'c_pupil.l': 16, 'c_toes_pinky2.l': 0, 'c_forearm_bend_proxy.r': 1, 'c_pinky1_proxy.r': 0, 'c_ring2.l': 0, 'c_stretch_arm_proxy.r': 1, 'c_eye_target.x': 0, 'c_root_bend.x': 1, 'c_morph_lip_up_size': 16, 'c_wrist_bend_proxy.l': 1, 'c_ring1_base_proxy.l': 0, 'c_head.x': 0, 'c_stretch_leg_proxy.l': 1, 'c_elbow_bend_proxy.r': 1, 'c_foot_fk.l': 0, 'c_arm_twist_offset.r': 0, 'c_toes_pinky1_proxy.r': 0, 'c_lips_roll_top_proxy.x': 0, 'c_lips_top_01.r': 0, 'layer_disp_main': 16, 'c_thigh_bend_01_proxy.l': 1, 'c_iris.l': 16, 'c_eyelid_corner_01_proxy.r': 1, 'c_lips_bot.l': 0, 'c_lips_bot_01.r': 0, 'c_root_bend_proxy.x': 1, 'c_eyebrow_full.r': 0, 'c_toes_middle1_proxy.l': 0, 'c_middle3.l': 0, 'c_arm_bend.l': 1, 'c_thigh_b.l': 1, 'c_hand_ik.l': 0, 'c_stretch_arm.l': 1, 'c_foot_ik_proxy.l': 0, 'c_spine_01_bend_proxy.x': 1, 'c_foot_fk_proxy.l': 0, 'c_lips_top_proxy.l': 0, 'c_toes_ring3_proxy.l': 0, 'c_lips_top.l': 0, 'c_stretch_arm_proxy.l': 1, 'c_eyelid_corner_02_proxy.r': 1, 'c_index1_base.l': 0, 'c_ankle_bend.l': 1, 'c_eye.r': 0, 'c_bot_bend_proxy.r': 1, 'c_foot_roll_cursor.l': 0, 'c_hand_ik.r': 0, 'c_eyebrow_02_proxy.r': 0, 'c_toes_middle1.r': 0, 'c_middle2_proxy.l': 0, 'c_stretch_arm_pin_proxy.r': 1, 'c_leg_bend_01_proxy.r': 1, 'c_eyebrow_01.l': 0, 'c_eyelid_top_01.l': 1, 'c_eye_proxy.l': 0, 'c_ankle_bend_proxy.l': 1, 'c_morph_lip_bot_size': 16, 'c_leg_fk_proxy.r': 0, 'c_stretch_leg_pin.l': 1, 'c_eye_offset_proxy.l': 1, 'c_lips_corner_mini.l': 0, 'c_shoulder_bend_proxy.l': 1, 'c_pos': 0, 'c_foot_ik.r': 0, 'c_knee_bend_proxy.l': 1, 'c_lips_bot_proxy.r': 0, 'c_tail_00_proxy.x': 0, 'c_spine_02_proxy.x': 0, 'c_toes_pinky3.r': 0, 'c_tong_03_proxy.x': 0, 'c_thumb1_base_proxy.r': 0, 'c_stretch_arm_pin.l': 1, 'c_leg_bend_02_proxy.l': 1, 'c_stretch_leg.l': 1, 'c_thumb1_proxy.r': 0, 'c_wrist_bend_proxy.r': 1}  

bone_update_locations = {'c_breast_01_proxy.l': (Vector((0.04883772134780884, -0.5081361532211304, -2.3916122913360596)), Vector((0.04883772134780884, -0.5081361532211304, -2.3670592308044434))), 'c_spine_01_proxy.x': (Vector((-2.3961765691637993e-06, -0.5081361532211304, -2.4267547130584717)), Vector((-2.3961765691637993e-06, -0.5081361532211304, -2.4161593914031982))), 'c_spine_02_bend_proxy.x': (Vector((-0.00014736957382410765, -0.5081361532211304, -2.3936164379119873)), Vector((0.0038200942799448967, -0.5081361532211304, -2.3936164379119873))), 'c_breast_02_proxy.l': (Vector((0.04825196415185928, -0.5218240022659302, -2.3574445247650146)), Vector((0.04825196415185928, -0.49444830417633057, -2.3574445247650146))), 'c_spine_02_proxy.x': (Vector((0.0, -0.508139967918396, -2.3380000591278076)), Vector((0.0, -0.508139967918396, -2.327312469482422))), 'c_breast_01_proxy.r': (Vector((-0.04883772134780884, -0.5081361532211304, -2.3916122913360596)), Vector((-0.04883772134780884, -0.5081361532211304, -2.3670592308044434))), 'c_root_master_proxy.x': (Vector((-2.3961765691637993e-06, -0.5081361532211304, -2.530362367630005)), Vector((-2.3961765691637993e-06, -0.5081361532211304, -2.5166168212890625))), 'c_root_proxy.x': (Vector((-2.3961765691637993e-06, -0.5074262022972107, -2.5002286434173584)), Vector((-2.3961765691637993e-06, -0.5074262022972107, -2.489633321762085))), 'c_spine_01_bend_proxy.x': (Vector((-0.00014736957382410765, -0.5081361532211304, -2.4434287548065186)), Vector((0.0038200942799448967, -0.5081361532211304, -2.4434287548065186))), 'c_root_bend_proxy.x': (Vector((-0.00014736957382410765, -0.5081361532211304, -2.481240749359131)), Vector((0.0038200942799448967, -0.5081361532211304, -2.481240749359131))), 'c_breast_02_proxy.r': (Vector((-0.04825196415185928, -0.5218240022659302, -2.3574445247650146)), Vector((-0.04825196415185928, -0.49444830417633057, -2.3574445247650146))), 'c_waist_bend_proxy.x': (Vector((0.03724130615592003, -0.5081361532211304, -2.4630987644195557)), Vector((0.041208770126104355, -0.5081361532211304, -2.4630987644195557)))}  