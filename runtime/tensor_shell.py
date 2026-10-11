"""Exact finite oriented triangle-shell checks and non-erasing coordinate updates.

Checks combinatorial manifold closure; does not certify spatial self-intersection
absence or infer continuous curvature from discrete shell counts.
"""
from collections import defaultdict
from copy import deepcopy

SCHEMA = 'keddeh.tensor-shell.v1'


def triple(value):
    if type(value) is not list or len(value) != 3 or any(type(x) is not int or abs(x) > 2**63-1 for x in value):
        raise ValueError('Coordinates require three bounded signed integers')
    return tuple(value)


def transition(state, displacement, *, reverse=False):
    if type(state) is not dict or set(state) != {'identity', 'origin', 'orientation', 'coordinate', 'tick'}:
        raise ValueError('Invalid retained state')
    if any(type(state[k]) is not str or not state[k] for k in ('identity', 'origin')):
        raise ValueError('Identity and symbolic origin must remain assigned')
    if type(state['tick']) is not int or state['tick'] < 0 or type(reverse) is not bool:
        raise ValueError('Invalid transition context')
    q, delta, orientation = triple(state['coordinate']), triple(displacement), triple(state['orientation'])
    if any(x not in (-1, 1) for x in orientation):
        raise ValueError('Orientation requires explicit signs')
    result = deepcopy(state)
    result['coordinate'] = [(-1 if reverse else 1) * (x + d) for x, d in zip(q, delta)]
    triple(result['coordinate'])
    result['orientation'] = [(-x if reverse else x) for x in orientation]
    result['tick'] += 1
    return result


def norm_shell_count(metric, radius):
    if type(radius) is not int or radius < 1 or metric not in ('L1', 'Linf'):
        raise ValueError('Positive integer radius and supported lattice metric required')
    return (4 if metric == 'L1' else 8) * radius


def validate_shell(shell):
    if type(shell) is not dict or set(shell) != {'schema', 'identity', 'origin', 'vertices', 'faces'} or shell['schema'] != SCHEMA:
        raise ValueError('Invalid tensor shell fields')
    if any(type(shell[k]) is not str or not shell[k] for k in ('identity', 'origin')):
        raise ValueError('Assigned identity and symbolic origin required')
    if type(shell['vertices']) is not list or not 4 <= len(shell['vertices']) <= 10000:
        raise ValueError('Vertex budget exceeded')
    vertices = [triple(v) for v in shell['vertices']]
    if len(set(vertices)) != len(vertices):
        raise ValueError('Duplicate vertex coordinates')
    faces = shell['faces']
    if type(faces) is not list or not 4 <= len(faces) <= 20000:
        raise ValueError('Face budget exceeded')
    edges, links, neighbors = defaultdict(list), defaultdict(list), defaultdict(set)
    normals = [0, 0, 0]
    volume6 = 0
    seen = set()
    for i, face in enumerate(faces):
        if type(face) is not list or len(face) != 3 or any(type(x) is not int or not 1 <= x <= len(vertices) for x in face) or len(set(face)) != 3:
            raise ValueError('Faces require distinct one-origin vertex references')
        if tuple(sorted(face)) in seen:
            raise ValueError('Duplicate face')
        seen.add(tuple(sorted(face)))
        a, b, c = (vertices[x-1] for x in face)
        u, v = tuple(y-x for x,y in zip(a,b)), tuple(y-x for x,y in zip(a,c))
        n = (u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0])
        if n == (0,0,0):
            raise ValueError('Degenerate face')
        normals = [x+y for x,y in zip(normals,n)]
        volume6 += a[0]*(b[1]*c[2]-b[2]*c[1])+a[1]*(b[2]*c[0]-b[0]*c[2])+a[2]*(b[0]*c[1]-b[1]*c[0])
        for j in range(3):
            x,y,z=face[j],face[(j+1)%3],face[(j+2)%3]
            edges[tuple(sorted((x,y)))].append((i,x,y))
            links[x].append((y,z))
    for incident in edges.values():
        if len(incident) != 2 or incident[0][1:] != incident[1][1:][::-1]:
            raise ValueError('Open, nonmanifold or inconsistently oriented edge')
        a,b=incident[0][0],incident[1][0]
        neighbors[a].add(b); neighbors[b].add(a)
    if len(links) != len(vertices):
        raise ValueError('Unused vertex')
    for pairs in links.values():
        graph=defaultdict(set)
        for a,b in pairs:
            graph[a].add(b); graph[b].add(a)
        if any(len(v) != 2 for v in graph.values()):
            raise ValueError('Nonmanifold vertex link')
        visited=set(); pending=[next(iter(graph))]
        while pending:
            node=pending.pop()
            if node not in visited:
                visited.add(node); pending.extend(graph[node]-visited)
        if len(visited) != len(graph):
            raise ValueError('Disconnected vertex link')
    visited=set(); pending=[0]
    while pending:
        node=pending.pop()
        if node not in visited:
            visited.add(node); pending.extend(neighbors[node]-visited)
    if len(visited) != len(faces) or normals != [0,0,0] or volume6 == 0:
        raise ValueError('Disconnected or zero-volume shell')
    return {'identity': shell['identity'], 'origin': shell['origin'], 'vertex_origin': 1,
            'vertices': len(vertices), 'edges': len(edges), 'faces': len(faces),
            'euler_characteristic': len(vertices)-len(edges)+len(faces),
            'oriented_area_vector_twice': normals, 'signed_volume_times_six': volume6,
            'closed_oriented_combinatorial_manifold': True,
            'spatial_self_intersection_checked': False}
