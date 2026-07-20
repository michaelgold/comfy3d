import bpy

def get_current_mode():
    return bpy.context.mode


def restore_current_mode(current_mode):
    if current_mode == 'EDIT_ARMATURE':
        current_mode = 'EDIT'
    if current_mode == "EDIT_MESH":
        current_mode = "EDIT"
    bpy.ops.object.mode_set(mode=current_mode)
    
    
def simplify_scene(self):        
    self.simplify_value = bpy.context.scene.render.use_simplify
    self.simplify_subd = bpy.context.scene.render.simplify_subdivision
    bpy.context.scene.render.use_simplify = True
    bpy.context.scene.render.simplify_subdivision = 0
    
    
def restore_simplify(self):
    bpy.context.scene.render.use_simplify = self.simplify_value
    bpy.context.scene.render.simplify_subdivision = self.simplify_subd
    
    
def disable_autokeyf():
    cur_state = bpy.context.scene.tool_settings.use_keyframe_insert_auto
    bpy.context.scene.tool_settings.use_keyframe_insert_auto = False
    return cur_state
    
    
def restore_autokeyf(cur_state):
    bpy.context.scene.tool_settings.use_keyframe_insert_auto = cur_state
