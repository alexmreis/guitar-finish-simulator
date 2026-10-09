"""Use exact derivatives of the modeled forearm surface for top shading."""
import math
from mathutils import Vector

def apply(body,thickness):
    mesh=body.data;mesh.update()
    normals=[tuple(n.vector) for n in mesh.corner_normals]
    changed=0
    for face in mesh.polygons:
        if face.normal.z<.85:continue
        for li in face.loop_indices:
            v=mesh.vertices[mesh.loops[li].vertex_index].co
            x,y,z=v
            wx=max(0,min(1,(-x-.06)/.10));wy=max(0,min(1,(.025-y)/.15));w=wx*wy
            expected=thickness/2-.007*w*w
            if abs(z-expected)>.00005:continue
            dx=.14*w*wy if 0<wx<1 else 0
            dy=(.014/.15)*w*wx if 0<wy<1 else 0
            normals[li]=tuple(Vector((-dx,-dy,1)).normalized());changed+=1
    mesh.normals_split_custom_set(normals)
    print('Analytic top normals assigned:',changed)
