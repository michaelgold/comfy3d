import bpy


def disable_overlays():
    curr_overlays = []
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    curr_overlays.append(space.overlay.show_overlays)
                    space.overlay.show_overlays = False
                    
    return curr_overlays
    
        
def restore_overlays(curr_overlays):
    i = 0
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':                 
                    space.overlay.show_overlays = curr_overlays[i]
                    i += 1


def set_resol(textured=False):
    scn = bpy.context.scene
    vs = scn.view_settings
    ds = scn.display_settings
    cur_resolx, cur_resoly = scn.render.resolution_x, scn.render.resolution_y
    curr_rend_perc = scn.render.resolution_percentage
    cur_film_transp = scn.render.film_transparent    
    cur_color_space = [ds.display_device, vs.view_transform, vs.look, vs.exposure, vs.gamma, vs.use_curve_mapping]
    
    scn.render.use_border = False
    scn.render.resolution_x = 256
    scn.render.resolution_y = 256
    scn.render.resolution_percentage = 100
    scn.render.image_settings.quality = 98
    scn.render.film_transparent = False
    
    has_set_profile = False
    try: 
        # color profile (default)
        ds.display_device = 'sRGB'
        vs.view_transform = 'Standard' if not textured else 'Filmic'
        has_set_profile = True
    except:
        pass
        
    if not has_set_profile:
        # ACES
        if os.environ.get("OCIO"):
            try:
                ds.display_device = 'P3-D65 - Display'
                vs.view_transform = 'Un-tone-mapped'
                print("Set ACES color profile")
            except:
                pass        
        
    vs.look = 'None'
    vs.exposure = 0.0
    vs.gamma = 1.0
    vs.use_curve_mapping = False    
    
    curr_media_type = None if bpy.app.version < (5,0,0) else scn.render.image_settings.media_type
    if bpy.app.version >= (5,0,0):
        scn.render.image_settings.media_type = 'IMAGE'
    curr_color_mode = scn.render.image_settings.color_mode
    curr_file_format = scn.render.image_settings.file_format
    scn.render.image_settings.color_mode = 'BW'
    scn.render.image_settings.file_format = 'JPEG'
    scn.render.use_stamp = False
    scn.render.use_multiview = False
    
    return cur_resolx, cur_resoly, curr_rend_perc, cur_film_transp, cur_color_space, curr_color_mode, curr_file_format, curr_media_type
    

def restore_resol(cur_resolx, cur_resoly, curr_rend_perc, cur_film_transp, cur_color_space, curr_color_mode, curr_file_format, curr_media_type):
    scn = bpy.context.scene
    vs = scn.view_settings
    ds = scn.display_settings
    
    if curr_file_format != '':# backward-compatibility with older Blender versions
        scn.render.image_settings.file_format = curr_file_format
    
    if bpy.app.version >= (5,0,0):
        scn.render.image_settings.media_type = curr_media_type
        
    scn.render.image_settings.color_mode = curr_color_mode
    scn.render.resolution_x, scn.render.resolution_y = cur_resolx, cur_resoly
    scn.render.resolution_percentage = curr_rend_perc
    scn.render.film_transparent = cur_film_transp    
    ds.display_device, vs.view_transform, vs.look, vs.exposure, vs.gamma, vs.use_curve_mapping = cur_color_space