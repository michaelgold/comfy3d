import bpy, bmesh
from .bone_data import *
from .version import *


def find_armature(mesh_obj):
    # the built-in function object.find_armature() is flawed,
    # returns None if multiple armature modifiers, and one of them is None.
    # Use this as a working alternative
    for mod in mesh_obj.modifiers:
        if mod.type == 'ARMATURE':
            if mod.object:
                return mod.object
                

def get_skinned_objects(armature):
    deformed_objects = []
    for ob in bpy.data.objects:
        if ob.type != 'MESH':
            continue
        if find_armature(ob) == None:
            continue
        if find_armature(ob).name == armature.name:
            deformed_objects.append(ob.name)
            
    return deformed_objects


def overwrite_vgroup(obj, vgroup, new_vgname):
    new_vgrp = obj.vertex_groups.get(new_vgname)                    
    if new_vgrp:
        obj.vertex_groups.remove(new_vgrp)
    vgroup.name = new_vgname


def export_mesh_data(mesh):
    _verts = [(v.co[0], v.co[1], v.co[2]) for v in mesh.vertices]
    _edges = [(edge.vertices[0], edge.vertices[1]) for edge in mesh.edges]
    _faces = []
    for face in mesh.polygons:
        face_verts = []
        for v in face.vertices:
            face_verts.append(v)
        _faces.append(face_verts)
        
    return _verts, _edges, _faces
    
    
def create_mesh_data(mesh_name, verts, edges, faces):
    # create an new mesh data given verts, edges and faces data
    new_mesh = bpy.data.meshes.new(name=mesh_name)
    new_mesh.from_pydata(verts, edges, faces)
    return new_mesh


def create_object_mesh(obj_name, verts, edges, faces):
    # create an new object with given mesh data
    shape_mesh = create_mesh_data(obj_name, verts, edges, faces)
    shape = bpy.data.objects.new(obj_name, shape_mesh)
    return shape
    
    
def create_object_mesh_empty(obj_name):
    _mesh = bpy.data.meshes.new(name=obj_name)
    _obj = bpy.data.objects.new(name=obj_name, object_data=_mesh)
    bpy.context.collection.objects.link(_obj)
    return _obj
    

def transfer_shape_keys(source_obj, target_obj):
    if source_obj == None or target_obj == None:
        return
    if source_obj.data.shape_keys == None:
        return
    
                
    source_shape_keys = source_obj.data.shape_keys.key_blocks    

    for sk_index, sk in enumerate(source_shape_keys):
        if sk_index == 0:# basis
            continue
        
        source_obj.active_shape_key_index = sk_index
        bpy.ops.object.shape_key_transfer()
        
        target_sk = target_obj.data.shape_keys.key_blocks.get(sk.name)
        target_sk.value = sk.value
        target_sk.slider_min, target_sk.slider_max = sk.slider_min, sk.slider_max
            
    source_obj.show_only_shape_key = False
    target_obj.show_only_shape_key = False

    
    # copy drivers
    anim_data = source_obj.data.shape_keys.animation_data

    if anim_data and anim_data.drivers:
        if target_obj.data.shape_keys:# If None, shape keys couldn't transfer previously, invalid modifier
            obj_anim_data = target_obj.data.shape_keys.animation_data_create()

            for fcurve in anim_data.drivers:
                new_fc = obj_anim_data.drivers.from_existing(src_driver=fcurve)
                new_fc.driver.is_valid = True

                for dvar in new_fc.driver.variables:
                    for dtar in dvar.targets:
                        if dtar.id == source_obj:
                            dtar.id = target_obj   
    
    
def transfer_shape_keys_deformed(source_obj, target_obj, apply_mods=False):  
    if source_obj == None or target_obj == None:
        return
  
    failed_sk = []

    #print("Disable mods...")    
    # disable all non-armature modifiers to solve issues when baking the mesh
    disabled_mod = {}
    if apply_mods == False:
        for obj in [source_obj, target_obj]:
            for mod in obj.modifiers:                
                if mod.type != "ARMATURE" and mod.show_viewport:           
                    mod.show_viewport = False
                    if not obj.name in disabled_mod:
                        disabled_mod[obj.name] = {}
                    disabled_mod[obj.name][mod.name] = mod.name
        
    if apply_mods:
        # enable viewport modifier level if render is enabled
        # necessary to bake mesh properly
        for mod in source_obj.modifiers:
            if mod.show_render:
                mod.show_viewport = True  
                
    if source_obj.data.shape_keys == None:
        return

    basis_index = 0
    
    # pin the Basis key
    #print("Pin Basis...")
    source_obj.active_shape_key_index = basis_index
    source_obj.show_only_shape_key = True
    #print("Update Depsgraph...")
    bpy.context.evaluated_depsgraph_get().update()

    # store the vert coords in basis shape keys
    #print("Store vert coords...")
    mesh_baked = bmesh.new()    
    if bpy.app.version < (2,93,0):
        mesh_baked.from_object(source_obj, bpy.context.evaluated_depsgraph_get(), deform=True, face_normals=False)
    elif bpy.app.version >= (2,93,0) and bpy.app.version < (3,0,2):
        mesh_baked.from_object(source_obj, bpy.context.evaluated_depsgraph_get(), face_normals=False)
    elif bpy.app.version >= (3,0,2):
        mesh_baked.from_object(source_obj, bpy.context.evaluated_depsgraph_get())#, cage=False, face_normals=False, vertex_normals=False)
        
    mesh_baked.verts.ensure_lookup_table()
    base_verts_coords = [i.co.copy() for i in mesh_baked.verts]

    if 'mesh_baked' in locals():
        del mesh_baked
        
    source_shape_keys = source_obj.data.shape_keys.key_blocks

    #print("Iterate through shapes...")
    for sk_index, sk in enumerate(source_shape_keys):

        if sk_index == basis_index:
            continue

        source_obj.active_shape_key_index = sk_index
        bpy.context.evaluated_depsgraph_get().update()

        # get the verts moved in shape key
        mesh_baked1 = bmesh.new()
        if bpy.app.version < (2,93,0):
            mesh_baked1.from_object(source_obj, bpy.context.evaluated_depsgraph_get(), deform=True, face_normals=False)
        elif bpy.app.version >= (2,93,0) and bpy.app.version < (3,0,2):
            mesh_baked1.from_object(source_obj, bpy.context.evaluated_depsgraph_get(), face_normals=False)
        elif bpy.app.version >= (3,0,2):
            mesh_baked1.from_object(source_obj, bpy.context.evaluated_depsgraph_get())#, cage=False, face_normals=False, vertex_normals=False)
        
        mesh_baked1.verts.ensure_lookup_table()        

        if len(mesh_baked1.verts) == len(base_verts_coords):       
            deformed_verts_coords = [i.co.copy() for i in mesh_baked1.verts]

            deformed_verts_index_list = []

            for vi, v in enumerate(mesh_baked1.verts):               
                if v.co != base_verts_coords[vi]:                   
                    deformed_verts_index_list.append(vi)
        

            # transfer the shape key
            #bpy.ops.object.shape_key_transfer()
            create_basis = False
            if target_obj.data.shape_keys == None:
                create_basis = True    
            elif len(target_obj.data.shape_keys.key_blocks) == 0:
                create_basis = True
            if create_basis:# add basis
                target_obj.shape_key_add(name='Basis')

            target_sk = target_obj.shape_key_add(name=sk.name, from_mix=False)
            target_sk.value = sk.value
            target_sk.slider_min, target_sk.slider_max = sk.slider_min, sk.slider_max
           
            #print('target_sk vert count:', len(target_sk.data))
            #print('mesh_baked1 vert count:', len(mesh_baked1.verts))
      
            # correct the deformed vert coordinates
            for deformed_vert_index in deformed_verts_index_list:
                #print("set vertex", deformed_vert_index, "from", target_sk.data[deformed_vert_index].co, "TO", mesh_baked1.verts[deformed_vert_index].co)
                if deformed_vert_index < len(target_sk.data):
                    target_sk.data[deformed_vert_index].co = mesh_baked1.verts[deformed_vert_index].co
                else:
                    if not sk.name in failed_sk:
                        failed_sk.append(sk.name)
                    print('Cannot transfer shape key, different amount of vertices. ShapeKey:', sk.name, 'Object:', source_obj.name, '> Aborting')

        else:# looks like a modifier is adding or removing verts from one shape key to another... not supported! (e.g Bevel, angle based, Decimate...)
            if not sk.name in failed_sk:
                failed_sk.append(sk.name)
            print('Cannot transfer shape key, different amount of vertices. ShapeKey:', sk.name, 'Object:', source_obj.name, '> Aborting')

        if 'mesh_baked1' in locals():
            del mesh_baked1

    source_obj.show_only_shape_key = False
    target_obj.show_only_shape_key = False

    # copy drivers
    anim_data = source_obj.data.shape_keys.animation_data

    if anim_data and anim_data.drivers:
        if target_obj.data.shape_keys:# If None, shape keys couldn't transfer previously, invalid modifier
            obj_anim_data = target_obj.data.shape_keys.animation_data_create()

            for fcurve in anim_data.drivers:
                new_fc = obj_anim_data.drivers.from_existing(src_driver=fcurve)
                new_fc.driver.is_valid = True

                for dvar in new_fc.driver.variables:
                    for dtar in dvar.targets:
                        if dtar.id == source_obj:
                            dtar.id = target_obj

    # restore disabled modifiers  
    for objname in disabled_mod:
        ob = bpy.data.objects.get(objname)
        for modname in disabled_mod[objname]:         
            ob.modifiers[modname].show_viewport = True
            
    return failed_sk
    
    
# Transfer weights with operators. Slower or faster than per vertex depending on the context
def transfer_weight_mod_operator(object=None, src_grp_name=None, tar_grp_name=None, replace=False):  
    mix_mod = object.modifiers.new(type='VERTEX_WEIGHT_MIX', name='ARP_VWM')  
    mix_mod.vertex_group_a = tar_grp_name
    mix_mod.vertex_group_b = src_grp_name
    mix_mod.mix_set = 'ALL'
    if replace:
        mix_mod.mix_mode = 'SET'
    else:
        mix_mod.mix_mode = 'ADD'
    
    # set in first position
    if bpy.app.version < (3,5,0):# backward-compatibility
        i_test = 0# safety check, some modifiers can't be moved, limit maximum trials
        while object.modifiers[0] != mix_mod and i_test < 50:
            i_test += 1
            bpy.ops.object.modifier_move_up(modifier=mix_mod.name)
    else:    
        object.modifiers.move(len(object.modifiers)-1, 0)
        
    bpy.ops.object.modifier_apply(modifier=mix_mod.name)

    
def transfer_weight_mod(object=None, dict=None, list=None, replace=False, tar_grp_name=""):
       
    #vgroups_copy = [i for i in object.vertex_groups]
    vgroups_names_copy = [i.name for i in object.vertex_groups]
    
    for vgroup_name in vgroups_names_copy:
        v_group = object.vertex_groups.get(vgroup_name)
        
        grp_name_base = get_bone_base_name(v_group.name)
        side = get_bone_side(v_group.name)
        
        if dict:
            if grp_name_base in dict:
                for tar_grp_base_name in dict[grp_name_base]:
                    if tar_grp_base_name.endswith('.x'):
                        side = side[:-2]
                    
                    tar_grp_name = tar_grp_base_name+side                  
                    if object.vertex_groups.get(tar_grp_name) == None:
                        object.vertex_groups.new(name=tar_grp_name)
                    
                    transfer_weight_mod_operator(object=object, src_grp_name=v_group.name, tar_grp_name=tar_grp_name, replace=replace)
                       
        if list:
            if grp_name_base in list:                
                if object.vertex_groups.get(tar_grp_name) == None:
                    object.vertex_groups.new(name=tar_grp_name)                    
                    
                transfer_weight_mod_operator(object=object, src_grp_name=v_group.name, tar_grp_name=tar_grp_name, replace=replace)
        
        
def transfer_weight_prefix_mod(object=None, prefix=None, tar_grp_base_name=None):
    
    vgroups_names_copy = [i.name for i in object.vertex_groups]# iterating over a copy fix bug: UnicodeDecodeError: 'utf-8' codec can't decode byte 0xb0 in position 1: invalid start byte
    
    for vgr_n in vgroups_names_copy:
        vgr = object.vertex_groups.get(vgr_n)
        
        if vgr.index == -1:            
            continue
        
        if vgr.name.startswith(prefix):
            side = vgr.name[-2:]
            tar_grp_name = tar_grp_base_name+side
            
            if object.vertex_groups.get(tar_grp_name):#if exists
                transfer_weight_mod_operator(object=object, src_grp_name=vgr.name, tar_grp_name=tar_grp_name)
                
                
def clamp_weight_mod(object=None, dict=None, list=None):
    
    for vg in object.vertex_groups:
        grp_name_base = get_bone_base_name(vg.name)
        side = get_bone_side(vg.name)
        
        if dict:
            if grp_name_base in dict:
                tar_grp_base_name = dict[grp_name_base]
                
                if tar_grp_base_name.endswith('.x'):
                    side = side[:-2]
                
                tar_grp_name = tar_grp_base_name+side
                tar_grp = object.vertex_groups.get(tar_grp_name)
                
                if tar_grp:
                    clamp_weight_mod_operator(object=object, src_grp_name=vg.name, tar_grp_name=tar_grp_name)
                    
                
def clamp_weight_mod_operator(object=None, src_grp_name=None, tar_grp_name=None):

    mix_mod = object.modifiers.new(type='VERTEX_WEIGHT_MIX', name='ARP_VWM')
    mix_mod.vertex_group_a = tar_grp_name
    mix_mod.vertex_group_b = src_grp_name
    mix_mod.mix_set = 'A'
    mix_mod.mix_mode = 'SET'
        
    # set in first position
    i_test = 0# safety check, some modifiers can't be moved
    while object.modifiers[0] != mix_mod and i_test < 50:
        i_test += 1
        bpy.ops.object.modifier_move_up(modifier="ARP_VWM")
    
    # apply
    bpy.ops.object.modifier_apply(modifier='ARP_VWM')
    
 
def multiply_weight_mod_operator(object=None, tar_grp_name='', fac=0.5):
    
    mix_mod = object.modifiers.new(type='VERTEX_WEIGHT_MIX', name='ARP_VWM')
    mix_mod.vertex_group_a = tar_grp_name
    mix_mod.mix_set = 'ALL'
    mix_mod.mix_mode = 'SET'
    mix_mod.mask_constant = 1 - fac
    
    # set in first position
    i_test = 0# safety check, some modifiers can't be moved
    while object.modifiers[0] != mix_mod and i_test < 50:
        i_test += 1
        bpy.ops.object.modifier_move_up(modifier="ARP_VWM")
    
    # apply
    bpy.ops.object.modifier_apply(modifier='ARP_VWM')

 
def multiply_weight_mod(object=None, dict=None):  
    
    for _vg in object.vertex_groups:    
        grp_name_base = get_bone_base_name(_vg.name)
        side = get_bone_side(_vg.name)
        
        if grp_name_base in dict:
            fac = dict[grp_name_base]
            multiply_weight_mod_operator(object=object, tar_grp_name=_vg.name, fac=fac)         
            

# Transfer weights functions per vertex. Slower or faster than operator depending on the context 
def transfer_weight_verts(object=None, dict=None, list=None, target_group_name=None, use_side=False):
    for vert in object.data.vertices:
        if len(vert.groups) == 0:
            continue
        
        # operate on a copy, creating vgroups in the same loop corrupts pointers on Mac OS
        grps_dict = {object.vertex_groups[grp.group].name: grp.weight for grp in vert.groups if grp.group < len(object.vertex_groups)}# sic, there may be corrupted vgroup ID anyway
   
        for grp_name in grps_dict:
            weight = grps_dict[grp_name]
            transfer_weight(object=object, vertice=vert, vertex_weight=weight, group_name=grp_name, dict=dict, list=list, target_group_name=target_group_name, use_side=use_side)
            
                        
def transfer_weight(object=None, vertice=None, vertex_weight=None, group_name=None, dict=None, list=None, target_group_name=None, use_side=False):    
    grp_name_base = get_bone_base_name(group_name) if not use_side else group_name
    side = '' if use_side else get_bone_side(group_name)

    # Dict mode
    if dict:
        if grp_name_base in dict:
            for target_grp in dict[grp_name_base]:
                if target_grp.endswith('.x') and not use_side:
                    side = side[:-2]

                target_group_name = target_grp+side
                target_group = object.vertex_groups.get(target_group_name)
                if target_group == None:
                    target_group = object.vertex_groups.new(name=target_group_name)

                target_group.add([vertice.index], vertex_weight, 'ADD')

   
    # List mode
    if list:
        if grp_name_base in list:
            target_group = object.vertex_groups.get(target_group_name)
            if target_group == None:
                target_group = object.vertex_groups.new(name=target_group_name)
                
            target_group.add([vertice.index], vertex_weight, 'ADD')


def transfer_weight_prefix_verts(object=None, prefix='', tar_grp_base_name=''):
    for vert in object.data.vertices:
        if len(vert.groups) == 0:
            continue

        for grp in vert.groups:
            try:
                grp_name = object.vertex_groups[grp.group].name
            except:
                continue
                
            transfer_weight_prefix(object=object, vertice=vert, vertex_weight=grp.weight, group_name=grp_name, prefix=prefix, target_group=tar_grp_base_name)
            
    
def transfer_weight_prefix(object=None, vertice=None, vertex_weight=None, group_name=None, prefix='', target_group=''):
    if group_name.startswith(prefix):
        side = group_name[-2:]
        tar_group_name = target_group+side
        if object.vertex_groups.get(tar_group_name):# if exists
            object.vertex_groups[tar_group_name].add([vertice.index], vertex_weight, 'ADD')

       
def copy_vgroup(object=None, dict=None, use_side=False, copy_method='OPERATOR'):
    # dict = {'arm_stretch': ['c_arm_twist_offset'],...}
    vgroups_names_copy = [i.name for i in object.vertex_groups]
    
    for vg_name in vgroups_names_copy:
        vg = object.vertex_groups.get(vg_name)
        #print(vg.index)
        #print('vg.name', vg.name)
        grp_name_base = get_bone_base_name(vg.name) if not use_side else vg.name
        side = get_bone_side(vg.name) if not use_side else ''
        
        if grp_name_base in dict:      
            tar_grp_names = dict[grp_name_base]
            for tar_grp_name in tar_grp_names:
                tar_grp = object.vertex_groups.get(tar_grp_name+side)
                if tar_grp == None:
                    continue
                    
                # remove current tar group
                object.vertex_groups.remove(tar_grp)
                # copy source group
                object.vertex_groups.active_index = vg.index
                if copy_method == 'OPERATOR':
                    bpy.ops.object.vertex_group_copy()
                    copy_idx = object.vertex_groups.active_index
                    copy_grp = object.vertex_groups[copy_idx]
                    copy_grp.name = tar_grp_name+side
                    
                elif copy_method == 'RAW':
                    copy_grp = object.vertex_groups.new(name=tar_grp_name+side)
                    for vert in object.data.vertices:
                        try:      
                            weight = vg.weight(vert.index)
                            copy_grp.add([vert.index], weight, 'REPLACE')
                        except:
                            continue
                
                
def copy_vertex_group(obj, source_vg_name, new_vg_name):
    source_vg = obj.vertex_groups.get(source_vg_name) 
    
    
            
            
def multiply_weight(object=None, vertice=None, vertex_weight=None, group_name=None, dict=None):
    grp_name_base = get_bone_base_name(group_name)
    side = get_bone_side(group_name)

    if grp_name_base in dict:
        if object.vertex_groups.get(group_name) != None:#if exists
            object.vertex_groups[group_name].add([vertice.index], vertex_weight * dict[grp_name_base], 'REPLACE')
            
            
def clamp_weights(object=None, vertice=None, vertex_weight=None, group_name=None, dict=None):

    grp_name_base = group_name[:-2]
    side = group_name[-2:]

    if "_dupli_" in group_name:
        grp_name_base = group_name[:-12]
        side = "_" + group_name[-11:]

    if grp_name_base in dict:
        if dict[grp_name_base][-2:] == '.x':
            side = ''

        _target_group = dict[grp_name_base]+side
        target_weight = 0.0

        if object.vertex_groups.get(_target_group) != None:
            for grp in vertice.groups:
                if object.vertex_groups[grp.group].name == _target_group:
                    target_weight = grp.weight

        def_weight = min(vertex_weight, target_weight)
        object.vertex_groups[group_name].add([vertice.index], def_weight, 'REPLACE')        
       

def count_closed_mesh_elements(obj):
    # count the amount of islands/closed elements contained in the same mesh object
    if obj.type != 'MESH':
        print("Cannot count mesh elements, not a mesh:", obj.name)
        return 0

    # Create a BMesh from the object's mesh data
    bm = bmesh.new()
    bm.from_mesh(obj.data)

    # Find connected components
    islands = []
    visited_faces = set()

    for face in bm.faces:
        if face.index not in visited_faces:
            # Perform a breadth-first search (BFS) to find all connected faces
            island = set()
            stack = [face]

            while stack:
                current_face = stack.pop()
                if current_face.index not in visited_faces:
                    visited_faces.add(current_face.index)
                    island.add(current_face.index)

                    # Add neighboring faces to the stack
                    for edge in current_face.edges:
                        for linked_face in edge.link_faces:
                            if linked_face.index not in visited_faces:
                                stack.append(linked_face)

            islands.append(island)

    # Free the BMesh
    bm.free()

    # Count the islands
    return len(islands)
