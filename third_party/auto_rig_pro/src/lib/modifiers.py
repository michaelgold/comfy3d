import bpy
from .version import *


def apply_modifier(mod_name):     
    try:# crash if modifier is viewport disabled
        if bpy.app.version >= (2,90,0):
            bpy.ops.object.modifier_apply(modifier=mod_name)
        else:
                bpy.ops.object.modifier_apply(apply_as="DATA", modifier=mod_name)
    except:
        print('Modifier could not be applied: '+mod_name)
        pass