import bpy, random


def clear_custom_normals(_obj):
    # Body temp mesh clean up
    #   clear normals    
    if bpy.app.version >= (4,0,0):# backward-compatibility, attr.is_required is not implemented before
        for attri in _obj.data.attributes:
            if not attri.is_required:
                if attri.name in ['sharp_edge', 'custom_normal']:
                    _obj.data.attributes.remove(attri)    
           
    bpy.ops.object.shade_smooth()
    
    #   clean topo
    bpy.ops.object.mode_set(mode='EDIT')
    
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=0.00001, use_unselected=True, use_sharp_edge_from_normals=False)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    
    bpy.ops.object.shade_smooth()
    
    
def get_current_shading():
    current_area = bpy.context.area
    
    for sview in current_area.spaces:
        if sview.type == 'VIEW_3D':
            return sview.shading.type
            
            
def switch_to_material_shading():
    cur_studio_light = []   
    scn = bpy.context.scene
    current_area = bpy.context.area
    
    for sview in current_area.spaces:
        if sview.type == "VIEW_3D":
            cur_studio_light.append(sview.shading.studio_light)
            
            if scn.sc_set_default_lighting:
                sview.shading.use_scene_lights = False
                sview.shading.use_scene_world = False
                # randomize env light
                envmaps = ['city.exr', 'courtyard.exr', 'forest.exr', 'interior.exr', 'night.exr', 'studio.exr', 'sunrise.exr', 'sunset.exr']
                sview.shading.studio_light = envmaps[random.randint(0, len(envmaps)-1)]
                sview.shading.studiolight_rotate_z = random.uniform(-3.14, 3.14)
                
                sview.shading.studiolight_intensity = 1.0
                sview.shading.studiolight_background_alpha = 0.0
                sview.shading.studiolight_background_blur = 0.5
                sview.shading.render_pass = 'COMBINED'
                sview.shading.use_compositor = 'DISABLED'
            
            theme_gradient = bpy.context.preferences.themes[0].view_3d.space.gradients.background_type
            theme_color = bpy.context.preferences.themes[0].view_3d.space.gradients.high_gradient 
            theme_color = (theme_color[0], theme_color[1], theme_color[2])
            print('theme_color', theme_color)
            
            bpy.context.preferences.themes[0].view_3d.space.gradients.background_type = 'SINGLE_COLOR'
            color_rand = random.uniform(0.16, 0.8)
            bpy.context.preferences.themes[0].view_3d.space.gradients.high_gradient = (color_rand, color_rand, color_rand)
    
    return cur_studio_light, theme_color, theme_gradient
    

def switch_to_solid_shading():
    cur_shade = []
    cur_studio_light = []
    cur_color_type = []
    cur_color_single = []
    cur_light = []
    cur_world_space_light = []
    cur_cavity = []
    cur_backg_type = []
    cur_backg_color = []
    cur_xray = []
    
    current_area = bpy.context.area
    
    for sview in current_area.spaces:
        if sview.type == "VIEW_3D":
            cur_shade.append(sview.shading.type)
            cur_studio_light.append(sview.shading.studio_light)
            cur_color_type.append(sview.shading.color_type)
            cur_color_single.append(sview.shading.single_color)            
            cur_light.append(sview.shading.light)
            cur_world_space_light.append(sview.shading.use_world_space_lighting)
            cur_cavity.append(sview.shading.show_cavity)
            cur_backg_type.append(sview.shading.background_type)
            cur_backg_color.append(sview.shading.background_color)
            cur_xray.append(sview.shading.show_xray)
            
            sview.shading.type = 'SOLID'            
            sview.shading.color_type = 'SINGLE'            
            sview.shading.single_color = (0.8,0.8,0.8)
            sview.shading.light = 'STUDIO'
            sview.shading.studio_light = 'Default'
            sview.shading.use_world_space_lighting = False
            sview.shading.show_cavity = False
            sview.shading.background_type = 'VIEWPORT'
            sview.shading.background_color = (0.040914, 0.0409144, 0.0409144)
            sview.shading.show_xray = False
            
            
    
    return cur_shade, cur_studio_light, cur_color_type, cur_color_single, cur_light, cur_world_space_light, cur_cavity, cur_backg_type, cur_backg_color, cur_xray
    

def restore_shading_texture(cur_studio_light, base_theme_color, theme_gradient):
    i = 0
    current_area = bpy.context.area
    for sview in current_area.spaces:
        if sview.type == "VIEW_3D":
            try:# backward-compatibility
                sview.shading.studio_light = cur_studio_light[i]
            except:
                pass
            bpy.context.preferences.themes[0].view_3d.space.gradients.high_gradient = base_theme_color
            bpy.context.preferences.themes[0].view_3d.space.gradients.background_type = theme_gradient
                
            i += 1
    
    
def restore_shading(cur_shade, cur_studio_light, cur_color_type, cur_color_single, cur_light, cur_world_space_light, cur_cavity, cur_backg_type, cur_backg_color, cur_xray):
    i = 0
    current_area = bpy.context.area
    for sview in current_area.spaces:
        if sview.type == "VIEW_3D":
            sview.shading.type = cur_shade[i]    
            sview.shading.color_type = cur_color_type[i]
            sview.shading.single_color = cur_color_single[i]
            sview.shading.light = cur_light[i]
            try:
                sview.shading.studio_light = cur_studio_light[i]
            except:
                pass
            sview.shading.use_world_space_lighting = cur_world_space_light[i]
            sview.shading.show_cavity = cur_cavity[i]
            sview.shading.background_type = cur_backg_type[i]
            sview.shading.background_color = cur_backg_color[i]
            sview.shading.show_xray = cur_xray[i]
            i += 1