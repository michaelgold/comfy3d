import bpy
from .version_arm_collec import *


def get_arm_col_idx(armature, name):
    for i, coll in enumerate(get_armature_collections(armature)):          
        if coll.name == name:
            return i
            
                
def sort_armature_collections(armature, only_collection=None, custom_collection=None, to_index=None):
    order = {'Main':0, 'Secondary':1, 'Deform':2, 'Reference':3}
    
    # sort a specific custom collection with custom index
    if custom_collection and to_index != None:
        cur_idx = get_arm_col_idx(armature, custom_collection)       
        armature.data.collections.move(cur_idx, to_index)
        return
      
    # sort collections as defined in the "order" dict
    for col_name in order:
        if only_collection:
            if only_collection != col_name:
                continue
                
        
        cur_idx = get_arm_col_idx(armature, col_name)
        to_idx = order[col_name]
        
        # check if collection is parented, if so, offset the index from the first sibling
        col = get_armature_collections(armature).get(col_name)
        if bpy.app.version >= (4,1,0) and col.parent:
            #print('Collection is parented:', col_name, 'get the first sibling index...')
            first_idx = 1000000
            for _c in get_armature_collections(armature):
                if _c.parent == col.parent and _c.index < first_idx:
                    first_idx = _c.index
            #print('First sibling is:', first_idx)
            to_idx += first_idx
            
        #print('Move from', cur_idx, 'to', to_idx)
        armature.data.collections.move(cur_idx, to_idx)
        

def get_parent_collections(target):
    # return the list of all parent collections to the specified target collection
    # with a recursive function. A sub-function is used, string based, to ease the process

    def get_parent_collections_string(target_name):
        parent_collections = ""
        found = None

        for collec in bpy.data.collections:
            for child in collec.children:
                if child.name == target_name:
                    #print("found", collec.name)
                    parent_collections += collec.name + ","
                    parent_collections += get_parent_collections_string(collec.name)

        return parent_collections


    string_result = get_parent_collections_string(target.name)
    to_list = [bpy.data.collections[i] for i in string_result[:-1].split(",") if i != ""]

    return to_list
    

def get_all_collections_viewlayer():
    def mt_traverse_tree(t):
        yield t
        for child in t.children:
            yield from mt_traverse_tree(child)

    colls = []
    coll = bpy.context.view_layer.layer_collection
    for c in mt_traverse_tree(coll):
        colls.append(c)
    return colls


def get_rig_collection(rig):
    if rig == None:
        return None
        
    for col in rig.users_collection:
        #if col.name.endswith('_rig'):
        return col        

    return None
    
    
def get_master_collection(rig_col):
    if rig_col == None:
        return None
        
    for col in bpy.data.collections:
        if len(col.children):
            for child_col in col.children:
                if child_col == rig_col:
                    return col
    return None
    
    
def get_cs_collection(col_master):   
    if col_master:
        for child_col in col_master.children:
            if len(child_col.objects):
                for o in child_col.objects:
                    if o.name.startswith('cs_grp'):
                        return child_col  
                        
    # the collection haven't been found, the collection hierarchy isn't correct
    # look for any collection called cs_grp
    for collec in bpy.data.collections:
        if collec.name.startswith("cs_grp"):
            return collec
            
    return None
            
            
def search_layer_collection(layerColl, collName):
    # Recursivly transverse layer_collection for a particular name
    found = None
    if (layerColl.name == collName):
        return layerColl
    for layer in layerColl.children:
        found = search_layer_collection(layer, collName)
        if found:
            return found
            
            
def set_collection_viz(collection_name, show, set_render=False):
    # set collection visibility
    # returns true if a change was necessary
    
    collection = bpy.data.collections.get(collection_name)
    collection_has_switched = False
    
    if collection:
        if collection.hide_viewport == show:
            collection.hide_viewport = not show
            collection_has_switched = True            
        
        layer_col = search_layer_collection(bpy.context.view_layer.layer_collection, collection_name)
        if layer_col:
            if layer_col.hide_viewport == show:
                layer_col.hide_viewport = not show
                collection_has_switched = True
        
        if set_render:
            if collection.hide_render == show:
                collection.hide_render = not show
                collection_has_switched = True
                
    if collection_has_switched:
        return True
        
        
def get_obj_collections(obj):
    # returns all collections that an object belongs to, including recursive parent collections
    collections = set()

    def find_parent_collections(collection):
        for parent in bpy.data.collections:
            if collection.name in parent.children.keys():
                collections.add(parent)
                find_parent_collections(parent)

    # Find all direct collections the object belongs to
    for collection in bpy.data.collections:
        if obj.name in collection.objects.keys():
            collections.add(collection)
            find_parent_collections(collection)

    return collections