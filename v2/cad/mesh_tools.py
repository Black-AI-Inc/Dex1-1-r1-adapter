import struct
from collections import Counter
import numpy as np

def validate_mesh(path):
    raw = path.read_bytes()
    n, = struct.unpack_from("<I", raw, 80)
    assert len(raw) == 84+50*n, "STL is not expected binary format"
    dtype=np.dtype([("normal", "<f4", 3), ("vertices", "<f4", (3,3)), ("attr", "<u2")])
    v = np.frombuffer(raw, dtype=dtype, count=n, offset=84)["vertices"].astype(float)
    # Weld STL's per-triangle vertices at one micrometre.
    verts, inverse = np.unique(np.round(v.reshape(-1,3), 5), axis=0, return_inverse=True)
    faces = inverse.reshape(-1,3)
    directed=Counter()
    edges=Counter()
    for a,b,c in faces:
        for i,j in [(a,b),(b,c),(c,a)]:
            edges[tuple(sorted((int(i),int(j))))] += 1
            directed[(int(i),int(j))] += 1
    assert all(c==2 for c in edges.values()), "Non-manifold or open STL"
    assert all(directed[(j,i)]==c for (i,j),c in directed.items()), "Inconsistent winding"
    signed_volume = np.einsum("ij,ij->i", v[:,0], np.cross(v[:,1],v[:,2])).sum()/6
    assert signed_volume > 0
    assert np.min(v[:,:,2]) > -1e-4
    return {"triangles": n, "watertight": True, "consistent_winding": True,
            "signed_volume_mm3": float(signed_volume),
            "bounds_mm": [verts.min(0).tolist(), verts.max(0).tolist()]}

