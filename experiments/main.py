import torch
import numpy as np
import polyscope as ps

from tqdm import trange
from mlp import *

# TODO: 4 complex version so test if mlp degrades with more complexes
# also test various scales to check normal vector losses...

def flat(sample_rate=16):
    complexes = np.array([[0, 1, 2, 3]])
    points = []

    # [0, 1] dimensions
    for i in range(sample_rate):
        for j in range(sample_rate):
            v = np.array([i, 0, j]) / sample_rate
            points.append(v)

    points = np.array(points)
    corners = [ points[0], points[sample_rate - 1], points[-1], points[-sample_rate] ]
    return complexes, points, np.array(corners)

def linear(sample_rate=16):
    complexes = np.array([[0, 1, 2, 3]])
    points = []

    # [0, 1] dimensions
    for i in range(sample_rate):
        for j in range(sample_rate):
            v = np.array([i, 0.25 * (i + j), j]) / sample_rate
            points.append(v)

    points = np.array(points)
    corners = [ points[0], points[sample_rate - 1], points[-1], points[-sample_rate] ]
    return complexes, points, np.array(corners)

def curved(sample_rate=16):
    complexes = np.array([[0, 1, 2, 3]])
    points = []

    # [0, 1] dimensions
    for i in range(sample_rate):
        for j in range(sample_rate):
            Y = 64.0 * ((i + j) / sample_rate) ** 2
            v = np.array([i, Y, j]) / sample_rate
            points.append(v)

    points = np.array(points)
    corners = [ points[0], points[sample_rate - 1], points[-1], points[-sample_rate] ]
    return complexes, points, np.array(corners)

def perlin(sample_rate=16):
    from perlin_noise import PerlinNoise

    noise = PerlinNoise(octaves=8, seed=1)
    complexes = np.array([[0, 1, 2, 3]])
    points = []

    # [0, 1] dimensions
    for i in range(sample_rate):
        for j in range(sample_rate):
            Y = 64.0 * noise([i / sample_rate, j / sample_rate])
            v = np.array([i, Y, j]) / sample_rate
            points.append(v)

    points = np.array(points)
    corners = [ points[0], points[sample_rate - 1], points[-1], points[-sample_rate] ]
    return complexes, points, np.array(corners)

# TODO: brick texture or so
def textured(sample_rate=16):
    from PIL import Image

    img = Image.open('displacements/fur.png')
    complexes = np.array([[0, 1, 2, 3]])
    points = []

    # [0, 1] dimensions
    for i in range(sample_rate):
        for j in range(sample_rate):
            u, v = i / sample_rate, j / sample_rate
            d = img.getpixel((u * img.width, v * img.height))
            # TODO: average...
            v = np.array([i, 0.1 * d[0], j]) / sample_rate
            points.append(v)

    points = np.array(points)
    corners = [ points[0], points[sample_rate - 1], points[-1], points[-sample_rate] ]
    return complexes, points, np.array(corners)

# TODO: custom 3D viewer...

def indices(C, sample_rate=16):
    triangles = []
    for c in range(C.shape[0]):
        offset = c * sample_rate * sample_rate
        for i in range(sample_rate - 1):
            for j in range(sample_rate - 1):
                a = offset + i * sample_rate + j
                c = offset + (i + 1) * sample_rate + j
                b, d = a + 1, c + 1
                triangles.append([a, b, c])
                triangles.append([b, d, c])

    return np.array(triangles)

# TODO: test different texture maps

experiments = {
    'flat': flat,
    'linear': linear,
    'curved': curved,
    'perlin': perlin,
    'textured': textured
}

models = {
        # 'simple': MLP_Simple,
        'pos-enc': MLP_Positional_Encoding,
        'feat-enc': MLP_Feature_Sinusoidal_Encoding,
        'feat-pos-enc': MLP_Feature_Position_Encoding,
        # 'uv': MLP_UV,
        'uv-enc': MLP_UV_Sinusoidal_Encoding,
        'uv-feat-uv-enc': MLP_Feature_UV_Sinusoidal_Encoding,
}

# TODO: also test different losses... (plain, +normal, +consistency loss), also using L1 for vertex/normal

# TODO: color wheel...

# TODO: two 64x64 layers... (test network size later?) compare to a single 128x128 (on the best performing)

# TODO: apply linear transformation to the input to probe the effects on vertex input space

ps.init()

# TODO: util... (including indices)
def lerp(X, U, V):
    lp00 = X[:, 0, :].unsqueeze(1) * U.unsqueeze(-1) * V.unsqueeze(-1)
    lp01 = X[:, 1, :].unsqueeze(1) * (1.0 - U.unsqueeze(-1)) * V.unsqueeze(-1)
    lp10 = X[:, 3, :].unsqueeze(1) * U.unsqueeze(-1) * (1.0 - V.unsqueeze(-1))
    lp11 = X[:, 2, :].unsqueeze(1) * (1.0 - U.unsqueeze(-1)) * (1.0 - V.unsqueeze(-1))
    return lp00 + lp01 + lp10 + lp11

def sample(complexes, corners, encodings, sample_rate):
    U = torch.linspace(0.0, 1.0, steps=sample_rate).cuda()
    V = torch.linspace(0.0, 1.0, steps=sample_rate).cuda()
    U, V = torch.meshgrid(U, V)

    corner_points = corners[complexes, :]
    corner_encodings = encodings[complexes, :]

    U, V = U.reshape(-1), V.reshape(-1)
    U = U.repeat((complexes.shape[0], 1))
    V = V.repeat((complexes.shape[0], 1))

    lerped_points = lerp(corner_points, U, V).reshape(-1, 3)
    lerped_encodings = lerp(corner_encodings, U, V).reshape(-1, POINT_ENCODING_SIZE)

    return lerped_points, lerped_encodings, torch.stack([U, V], dim=-1).squeeze(0)

sample_rate = 256
for i, (name, experiment) in enumerate(experiments.items()):
    # Generate reference
    complexes, target, corners = experiment(sample_rate)

    # Precompute indices
    triangles = indices(complexes, sample_rate)

    for j, (model_name, M) in enumerate(models.items()):
        # Load the model and parameters
        # m = MLP_Feature_UV_Sinusoidal_Encoding().cuda()
        m = M().cuda()

        tch_complexes = torch.from_numpy(complexes).int().cuda()
        tch_corners   = torch.from_numpy(corners).float().cuda()
        tch_encodings = torch.randn((target.shape[0], POINT_ENCODING_SIZE), requires_grad=True, dtype=torch.float32, device='cuda')

        tch_target = torch.from_numpy(target).float().cuda()

        # Compute reference normals
        tch_v0 = tch_target[triangles[:, 0], :]
        tch_v1 = tch_target[triangles[:, 1], :]
        tch_v2 = tch_target[triangles[:, 2], :]

        tch_e0 = tch_v1 - tch_v0
        tch_e1 = tch_v2 - tch_v0

        tch_normals = torch.cross(tch_e0, tch_e1, dim=1)

        # Train the model
        optimizer = torch.optim.Adam(list(m.parameters()) + [ tch_encodings ], lr=1e-2)

        history = []
        for _ in trange(1_000):
            # TODO: train the normals as well...
            # TODO: iterate of all losses...
            LP, LE, UV = sample(tch_complexes, tch_corners, tch_encodings, sample_rate)
            V = m(points=LP, encodings=LE, uv=UV)

            V0 = V[triangles[:, 0], :]
            V1 = V[triangles[:, 1], :]
            V2 = V[triangles[:, 2], :]

            E0 = V1 - V0
            E1 = V2 - V0

            normals = torch.cross(E0, E1, dim=1)

            loss = torch.mean(torch.norm(V - tch_target, dim=1)) + 10000.0 * torch.mean(torch.norm(normals - tch_normals, dim=1))

            history.append(loss.item())

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        print(f'{name}: from {history[0]:.3f} to {history[-1]:.3f}')

        # Final evaluation and visualization
        LP, LE, UV = sample(tch_complexes, tch_corners, tch_encodings, sample_rate)
        V = m(points=LP, encodings=LE, uv=UV)

        off_target = target + np.array([1.5 * i, 0, 0])
        ref_mesh = ps.register_surface_mesh(name, off_target, triangles, color=(0.5, 1.0, 0.5))
        ref_mesh.add_scalar_quantity('Y', target[:, 1], defined_on='vertices')

        off_model = V.detach().cpu().numpy() + np.array([1.5 * i, 0, 1.5 * (j + 1)])
        nsc_mesh = ps.register_surface_mesh(name + ':' + model_name, off_model, triangles, color=(0.5, 0.5, 1.0))
        nsc_mesh.add_scalar_quantity('Y', V[:, 1].detach().cpu().numpy(), defined_on='vertices')

    # TODO: local experimental model architectures...
    # try to feed procedural perlin noise as well (or check the nvidia paper)

    # TODO: also generate loss graphs for each case

ps.show()

