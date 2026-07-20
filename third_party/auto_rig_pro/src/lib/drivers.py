import bpy
from .objects import *
from .bone_pose import *
from .context import *


def remove_constraint_drivers(pb_name, cns_name):
    _dp_cns = 'pose.bones["'+pb_name+'"].constraints["'+cns_name+'"].'
    _to_del = []
    
    # collect constraint drivers
    for dra in bpy.context.active_object.animation_data.drivers:
        if dra.data_path.startswith(_dp_cns):
            _to_del.append((dra.data_path, dra.array_index))
    
    # remove
    for drdp in _to_del:
        _dp, arridx = drdp[0], drdp[1]
        drb = bpy.context.active_object.animation_data.drivers.find(_dp, index=arridx)
        if drb:# maybe superfluous
            bpy.context.active_object.animation_data.drivers.remove(drb)
            print("Removed cns driver:", _dp, arridx)

def add_driver_to_prop(obj, dr_dp, tar_dp, array_idx=-1, exp="var", multi_var=False):
    if obj.animation_data == None:
        obj.animation_data_create()
        
    drivers_list = obj.animation_data.drivers
    dr = drivers_list.find(dr_dp, index=array_idx)
    if dr == None:
        dr = obj.driver_add(dr_dp, array_idx)
    
    if multi_var == False:
        var = dr.driver.variables.get('var')
        if var == None:
            var = dr.driver.variables.new()
        var.name = 'var'
        var.type = 'SINGLE_PROP'        
        var.targets[0].id = obj
        var.targets[0].data_path = tar_dp
    else:# create multiple variables, tar_dp is a dict in that case
        for var_name in tar_dp:
            var = dr.driver.variables.get(var_name)
            if var == None:
                var = dr.driver.variables.new()
            var.name = var_name
            var.type = 'SINGLE_PROP'
            var.targets[0].id = obj
            var.targets[0].data_path = tar_dp[var_name]
            
    dr.driver.expression = exp
            
            
def get_pbone_name_from_data_path(dp):
    # return the pbone name from the driver data path   
    if not '"' in dp:
        return None
    return dp.split('"')[1]
    
    
def replace_driver_target_object(dr, current_obj_name, new_obj_name):
    # replace the given driver target object as set in the variables, with a new one
    for var in dr.driver.variables:
        for tar in var.targets:
            if tar.id == get_object(current_obj_name):
                tar.id = get_object(new_obj_name)
                
                
def copy_driver_variables(variables, source_driver, suffix):
    for v1 in variables:
        # create a variable
        clone_var = source_driver.driver.variables.new()
        clone_var.name = v1.name
        clone_var.type = v1.type

        # copy variable path
        try:
            clone_var.targets[0].data_path = v1.targets[0].data_path
            # increment bone data path name
            if '.r"]' in v1.targets[0].data_path:
                new_d_path = v1.targets[0].data_path
                new_d_path = new_d_path.replace('.r"]', suffix + '"]')

            if '.l"]' in v1.targets[0].data_path:
                new_d_path = v1.targets[0].data_path
                new_d_path = new_d_path.replace('.l"]', suffix + '"]')

            clone_var.targets[0].data_path = new_d_path

        except:
            print("no data_path for: " + v1.name)

        try:
            clone_var.targets[0].bone_target = v1.targets[0].bone_target

            if ".r" in v1.targets[0].bone_target:
                clone_var.targets[0].bone_target = v1.targets[0].bone_target.replace(".r", suffix)
            if ".l" in v1.targets[0].bone_target:
                clone_var.targets[0].bone_target = v1.targets[0].bone_target.replace(".l", suffix)


        except:
            print("no bone_target for: " + v1.name)
        try:
            clone_var.targets[0].transform_type = v1.targets[0].transform_type
        except:
            print("no transform_type for: " + v1.name)
        try:
            clone_var.targets[0].transform_space = v1.targets[0].transform_space
        except:
            print("no transform_space for: " + v1.name)
        try:
            clone_var.targets[0].id_type = v1.targets[0].id_type
        except:
            print("no id_type for: " + v1.name)
        try:
            clone_var.targets[0].id = v1.targets[0].id
        except:
            print("no id for: " + v1.name)
            
            
def remove_duplicated_drivers():
    arm = bpy.context.active_object  
    to_delete = []

    for i, dr in enumerate(arm.animation_data.drivers):
        found = False

        # find duplicates only if the current one is not already found
        for d in to_delete:
            if d[0] == dr.data_path and d[1] == dr.array_index:
                found = True
                break

        if not found:
            dp = dr.data_path
            array_idx = dr.array_index

            for j, dr1 in enumerate(arm.animation_data.drivers):
                if i != j:
                    if dp == dr1.data_path and array_idx == dr1.array_index:
                        to_delete.append([dp, array_idx])
                        
    print("Found", len(to_delete), "duplicated drivers")

    if len(to_delete) == 0:
        return        
    
    print("  delete them...")

    for dri in to_delete:
        try:
            arm.driver_remove(dri[0], dri[1])

        except:
            arm.driver_remove(dri[0], -1)


def remove_invalid_drivers():
    obj = bpy.context.active_object
    
    if obj.animation_data == None:
        return
    
    current_mode = bpy.context.mode
    bpy.ops.object.mode_set(mode='POSE')

    invalid_drivers_total = 0

    def is_driver_valid(dr, bone_name):
        if not dr.is_valid:
            return False
        if not obj.data.bones.get(bone_name):
            return False
        if "constraints" in dr.data_path:
            cns_name = dr.data_path.split('"')[3]
            target_bone = get_pose_bone(bone_name)
            found_cns = False

            if len(target_bone.constraints) > 0:
                for cns in target_bone.constraints:
                    if cns.name == cns_name:
                        found_cns = True
                if "cns" in locals():
                    del cns

            if not found_cns:
                return False

        return True

    for dr in obj.animation_data.drivers:
        if dr.data_path.startswith('pose.bones'):
            b = dr.data_path.split('"')[1]

            if not is_driver_valid(dr, b):
                # the driver is invalid
                # assign a dummy but valid data path since we can't remove drivers
                # with invalid data path
                # print("Invalid driver found:", dr.data_path)
                invalid_drivers_total += 1
                dr.array_index = 0
                dr.data_path = 'delta_scale'

    if 'dr' in locals():
        del dr

    #print("Found", invalid_drivers_total, "invalid drivers")

    count = 0
    for dr in obj.animation_data.drivers:
        if dr.data_path == "delta_scale":
            obj.animation_data.drivers.remove(dr)
            count += 1

    #print(count, "invalid drivers deleted")

    # restore saved mode
    restore_current_mode(current_mode)