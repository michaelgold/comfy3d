import bpy

def get_armature_collections(_arm): 
    arm_data = _arm.data if 'type' in dir(_arm) else _arm
    if bpy.app.version >= (4,1,0):
        return arm_data.collections_all
    else:
        return arm_data.collections