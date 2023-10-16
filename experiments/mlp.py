import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

POINT_ENCODING_SIZE = 20

class MLP_Simple(nn.Module):
    def __init__(self) -> None:
        super(MLP_Simple , self).__init__()

        # Pass configuration as constructor arguments
        self.encoding_linears = [
            nn.Linear(POINT_ENCODING_SIZE + 3, 64),
            nn.Linear(64, 64),
            nn.Linear(64, 64),
            nn.Linear(64, 3)
        ]

        self.encoding_linears = nn.ModuleList(self.encoding_linears)

    def forward(self, **kwargs):
        bases = kwargs['points']
        encodings = kwargs['encodings']

        X = torch.cat([ encodings, bases ], dim=-1)

        for i, linear in enumerate(self.encoding_linears):
            X = linear(X)
            if i < len(self.encoding_linears) - 1:
                X = torch.sin(X)

        return bases + X

class MLP_Positional_Encoding(nn.Module):
    # TODO: variable levels..
    L = 10

    def __init__(self) -> None:
        super(MLP_Positional_Encoding, self).__init__()

        # Pass configuration as constructor arguments
        self.encoding_linears = [
            nn.Linear(POINT_ENCODING_SIZE + (2 * self.L + 1) * 3, 64),
            nn.Linear(64, 64),
            nn.Linear(64, 64),
            nn.Linear(64, 3)
        ]

        self.encoding_linears = nn.ModuleList(self.encoding_linears)

    def forward(self, **kwargs):
        bases = kwargs['points']
        encodings = kwargs['encodings']

        X = [ encodings, bases ]
        for i in range(self.L):
            X += [ torch.sin(2 ** i * bases), torch.cos(2 ** i * bases) ]
        X = torch.cat(X, dim=-1)

        for i, linear in enumerate(self.encoding_linears):
            X = linear(X)
            if i < len(self.encoding_linears) - 1:
                X = torch.sin(X)

        return bases + X

class MLP_Positional_Encoding_Wide(nn.Module):
    # TODO: variable levels..
    L = 8

    def __init__(self) -> None:
        super(MLP_Positional_Encoding_Wide, self).__init__()

        # Pass configuration as constructor arguments
        self.encoding_linears = [
            nn.Linear(POINT_ENCODING_SIZE + (2 * self.L + 1) * 3, 128),
            nn.Linear(128, 128),
            nn.Linear(128, 3)
        ]

        self.encoding_linears = nn.ModuleList(self.encoding_linears)

    def forward(self, **kwargs):
        bases = kwargs['points']
        encodings = kwargs['encodings']

        X = [ encodings, bases ]
        for i in range(self.L):
            X += [ torch.sin(2 ** i * bases), torch.cos(2 ** i * bases) ]
        X = torch.cat(X, dim=-1)

        for i, linear in enumerate(self.encoding_linears):
            X = linear(X)
            if i < len(self.encoding_linears) - 1:
                X = torch.sin(X)

        return bases + X

class MLP_Positional_Morlet_Encoding(nn.Module):
    # TODO: variable levels..
    L = 8

    def __init__(self) -> None:
        super(MLP_Positional_Morlet_Encoding, self).__init__()

        # Pass configuration as constructor arguments
        self.encoding_linears = [
            nn.Linear(POINT_ENCODING_SIZE + (2 * self.L + 1) * 3, 64),
            nn.Linear(64, 64),
            nn.Linear(64, 64),
            nn.Linear(64, 3)
        ]

        self.encoding_linears = nn.ModuleList(self.encoding_linears)

        self.s0 = nn.Parameter(torch.tensor(1.0))
        self.w0 = nn.Parameter(torch.tensor(1.0))
        self.s1 = nn.Parameter(torch.tensor(1.0))
        self.w1 = nn.Parameter(torch.tensor(1.0))

    def forward(self, **kwargs):
        bases = kwargs['points']
        encodings = kwargs['encodings']

        X = [ encodings, bases ]
        for i in range(self.L):
            X += [ torch.sin(2 ** i * bases), torch.cos(2 ** i * bases) ]
        X = torch.cat(X, dim=-1)

        for i, linear in enumerate(self.encoding_linears):
            X = linear(X)
            if i < len(self.encoding_linears) - 1:
                if i == 0:
                    X = torch.exp(-self.s0 * X ** 2) * torch.sin(self.w0 * X)
                elif i == 1:
                    X = torch.exp(-self.s1 * X ** 2) * torch.sin(self.w1 * X)

        return bases + X

class MLP_Positional_Onion_Encoding(nn.Module):
    # TODO: variable levels..
    L = 10

    def __init__(self) -> None:
        super(MLP_Positional_Onion_Encoding, self).__init__()

        # Pass configuration as constructor arguments
        self.encoding_linears = [
            nn.Linear(POINT_ENCODING_SIZE + (2 * self.L + 1) * 3, 64),
            nn.Linear(64, 64),
            nn.Linear(64, 64),
            nn.Linear(64, 3)
        ]

        self.encoding_linears = nn.ModuleList(self.encoding_linears)

        self.s0 = nn.Parameter(torch.tensor(1.0))
        self.s1 = nn.Parameter(torch.tensor(1.0))

    def onion(self, x, s):
        softplus = torch.log(1 + torch.exp(x))
        sin = torch.sin(s * x)
        exp = torch.exp(-s * x ** 2)
        return softplus * sin * exp

    def forward(self, **kwargs):
        bases = kwargs['points']
        encodings = kwargs['encodings']

        X = [ encodings, bases ]
        for i in range(self.L):
            X += [ torch.sin(2 ** i * bases), torch.cos(2 ** i * bases) ]
        X = torch.cat(X, dim=-1)

        for i, linear in enumerate(self.encoding_linears):
            X = linear(X)
            if i < len(self.encoding_linears) - 1:
                X = self.onion(X, self.s0 if i == 0 else self.s1)

        return bases + X

# TODO: multidimensional locality?
# TODO: if wavelets are better, is a wider network better? since there will be more active wavelets?

class MLP_Feature_Sinusoidal_Encoding(nn.Module):
    L = 10

    def __init__(self) -> None:
        super(MLP_Feature_Sinusoidal_Encoding, self).__init__()

        # Pass configuration as constructor arguments
        self.encoding_linears = [
            nn.Linear((2 * self.L + 1) * POINT_ENCODING_SIZE + 3, 64),
            nn.Linear(64, 64),
            nn.Linear(64, 64),
            nn.Linear(64, 3)
        ]

        self.encoding_linears = nn.ModuleList(self.encoding_linears)

    def forward(self, **kwargs):
        bases = kwargs['points']
        encodings = kwargs['encodings']

        X = [ encodings ]
        for i in range(self.L):
            X += [ torch.sin(2 ** i * encodings), torch.cos(2 ** i * encodings) ]
        X += [ bases ]
        X = torch.cat(X, dim=-1)

        for i, linear in enumerate(self.encoding_linears):
            X = linear(X)
            if i < len(self.encoding_linears) - 1:
                X = torch.sin(X)

        return bases + X

class MLP_Feature_Morlet_Encoding(nn.Module):
    L = 10

    def __init__(self) -> None:
        super(MLP_Feature_Morlet_Encoding, self).__init__()

        # Pass configuration as constructor arguments
        self.encoding_linears = [
            nn.Linear((2 * self.L + 1) * POINT_ENCODING_SIZE + 3, 64),
            nn.Linear(64, 64),
            nn.Linear(64, 64),
            nn.Linear(64, 3)
        ]

        self.encoding_linears = nn.ModuleList(self.encoding_linears)

        self.s0 = nn.Parameter(torch.tensor(1.0))
        self.w0 = nn.Parameter(torch.tensor(1.0))
        self.s1 = nn.Parameter(torch.tensor(1.0))
        self.w1 = nn.Parameter(torch.tensor(1.0))

    def forward(self, **kwargs):
        bases = kwargs['points']
        encodings = kwargs['encodings']

        X = [ encodings ]
        for i in range(self.L):
            X += [ torch.sin(2 ** i * encodings), torch.cos(2 ** i * encodings) ]
        X += [ bases ]
        X = torch.cat(X, dim=-1)

        for i, linear in enumerate(self.encoding_linears):
            X = linear(X)
            if i < len(self.encoding_linears) - 1:
                if i == 0:
                    X = torch.exp(-self.s0 * X ** 2) * torch.sin(self.w0 * X)
                elif i == 1:
                    X = torch.exp(-self.s1 * X ** 2) * torch.sin(self.w1 * X)

        return bases + X

class MLP_Feature_Onion_Encoding(nn.Module):
    L = 10

    def __init__(self) -> None:
        super(MLP_Feature_Onion_Encoding, self).__init__()

        # Pass configuration as constructor arguments
        self.encoding_linears = [
            nn.Linear((2 * self.L + 1) * POINT_ENCODING_SIZE + 3, 64),
            nn.Linear(64, 64),
            nn.Linear(64, 64),
            nn.Linear(64, 3)
        ]

        self.encoding_linears = nn.ModuleList(self.encoding_linears)

        self.s0 = nn.Parameter(torch.tensor(1.0))
        self.s1 = nn.Parameter(torch.tensor(1.0))

    def onion(self, x, s):
        softplus = torch.log(1 + torch.exp(x))
        sin = torch.sin(s * x)
        exp = torch.exp(-s * x ** 2)
        return softplus * sin * exp

    def forward(self, **kwargs):
        bases = kwargs['points']
        encodings = kwargs['encodings']

        X = [ encodings ]
        for i in range(self.L):
            X += [ torch.sin(2 ** i * encodings), torch.cos(2 ** i * encodings) ]
        X += [ bases ]
        X = torch.cat(X, dim=-1)

        for i, linear in enumerate(self.encoding_linears):
            X = linear(X)
            if i < len(self.encoding_linears) - 1:
                X = self.onion(X, self.s0 if i == 0 else self.s1)

        return bases + X

class MLP_Feature_Position_Encoding(nn.Module):
    L = 16

    def __init__(self) -> None:
        super(MLP_Feature_Position_Encoding, self).__init__()

        # Pass configuration as constructor arguments
        self.encoding_linears = [
            nn.Linear((2 * self.L + 1) * (POINT_ENCODING_SIZE + 3), 64),
            nn.Linear(64, 64),
            nn.Linear(64, 64),
            nn.Linear(64, 3)
        ]

        self.encoding_linears = nn.ModuleList(self.encoding_linears)

    def forward(self, **kwargs):
        bases = kwargs['points']
        encodings = kwargs['encodings']

        X = [ encodings, bases ]
        for i in range(self.L):
            X += [ torch.sin(2 ** i * encodings), torch.cos(2 ** i * encodings) ]
            X += [ torch.sin(2 ** i * bases), torch.cos(2 ** i * bases) ]
        X = torch.cat(X, dim=-1)

        for i, linear in enumerate(self.encoding_linears):
            X = linear(X)
            if i < len(self.encoding_linears) - 1:
                X = torch.sin(X)

        return bases + X

# TODO: use UV output... (local positional encoding, forget about boundaries for now...)
class MLP_UV(nn.Module):
    def __init__(self) -> None:
        super(MLP_UV, self).__init__()

        # Pass configuration as constructor arguments
        self.encoding_linears = [
            nn.Linear(POINT_ENCODING_SIZE + 2, 64),
            nn.Linear(64, 64),
            nn.Linear(64, 64),
            nn.Linear(64, 3)
        ]

        self.encoding_linears = nn.ModuleList(self.encoding_linears)

    def forward(self, **kwargs):
        bases = kwargs['points']
        encodings = kwargs['encodings']
        uvs = kwargs['uv']

        # TODO: operate on dict of tensors
        X = torch.cat([ encodings, uvs ], dim=-1)

        for i, linear in enumerate(self.encoding_linears):
            X = linear(X)
            if i < len(self.encoding_linears) - 1:
                X = torch.sin(X)

        return bases + X

class MLP_UV_Sinusoidal_Encoding(nn.Module):
    L = 8

    def __init__(self) -> None:
        super(MLP_UV_Sinusoidal_Encoding, self).__init__()

        # Pass configuration as constructor arguments
        self.encoding_linears = [
            nn.Linear(POINT_ENCODING_SIZE + (2 * self.L + 1) * 2, 64),
            nn.Linear(64, 64),
            nn.Linear(64, 64),
            nn.Linear(64, 3)
        ]

        self.encoding_linears = nn.ModuleList(self.encoding_linears)

    def forward(self, **kwargs):
        bases = kwargs['points']
        encodings = kwargs['encodings']
        uvs = kwargs['uv']

        # TODO: operate on dict of tensors
        X = [ encodings, uvs ]
        for i in range(self.L):
            X += [ torch.sin(2 ** i * uvs), torch.cos(2 ** i * uvs) ]
        X = torch.cat(X, dim=-1)

        for i, linear in enumerate(self.encoding_linears):
            X = linear(X)
            if i < len(self.encoding_linears) - 1:
                X = torch.sin(X)

        return bases + X

class MLP_Feature_UV_Sinusoidal_Encoding(nn.Module):
    L = 8

    def __init__(self) -> None:
        super(MLP_Feature_UV_Sinusoidal_Encoding, self).__init__()

        # Pass configuration as constructor arguments
        self.encoding_linears = [
            nn.Linear((2 * self.L + 1) * (2 + POINT_ENCODING_SIZE), 64),
            nn.Linear(64, 64),
            nn.Linear(64, 64),
            nn.Linear(64, 3)
        ]

        self.encoding_linears = nn.ModuleList(self.encoding_linears)

    def forward(self, **kwargs):
        bases = kwargs['points']
        encodings = kwargs['encodings']
        uvs = kwargs['uv']

        # TODO: operate on dict of tensors
        X = [ encodings, uvs ]
        for i in range(self.L):
            X += [ torch.sin(2 ** i * encodings), torch.cos(2 ** i * encodings) ]
            X += [ torch.sin(2 ** i * uvs), torch.cos(2 ** i * uvs) ]
        X = torch.cat(X, dim=-1)

        for i, linear in enumerate(self.encoding_linears):
            X = linear(X)
            if i < len(self.encoding_linears) - 1:
                X = torch.sin(X)

        return bases + X

class MLP_Position_UV_Sinusoidal_Encoding(nn.Module):
    L = 8

    def __init__(self) -> None:
        super(MLP_Position_UV_Sinusoidal_Encoding, self).__init__()

        # Pass configuration as constructor arguments
        self.encoding_linears = [
            nn.Linear((2 * self.L + 1) * (2 + 3) + POINT_ENCODING_SIZE, 64),
            nn.Linear(64, 64),
            nn.Linear(64, 64),
            nn.Linear(64, 3)
        ]

        self.encoding_linears = nn.ModuleList(self.encoding_linears)

    def forward(self, **kwargs):
        bases = kwargs['points']
        encodings = kwargs['encodings']
        uvs = kwargs['uv']

        # TODO: operate on dict of tensors
        X = [ encodings, bases, uvs ]
        for i in range(self.L):
            X += [ torch.sin(2 ** i * bases), torch.cos(2 ** i * bases) ]
            X += [ torch.sin(2 ** i * uvs), torch.cos(2 ** i * uvs) ]
        X = torch.cat(X, dim=-1)

        for i, linear in enumerate(self.encoding_linears):
            X = linear(X)
            if i < len(self.encoding_linears) - 1:
                X = torch.sin(X)

        return bases + X

class MLP_UV_Morlet_Encoding(nn.Module):
    L = 8

    def __init__(self) -> None:
        super(MLP_UV_Morlet_Encoding, self).__init__()

        # Pass configuration as constructor arguments
        self.encoding_linears = [
            nn.Linear((2 * self.L + 1) * 2 + 3 + POINT_ENCODING_SIZE, 64),
            nn.Linear(64, 64),
            nn.Linear(64, 64),
            nn.Linear(64, 3)
        ]

        self.encoding_linears = nn.ModuleList(self.encoding_linears)

        self.s0 = nn.Parameter(torch.tensor(1.0))
        self.w0 = nn.Parameter(torch.tensor(1.0))
        self.s1 = nn.Parameter(torch.tensor(1.0))
        self.w1 = nn.Parameter(torch.tensor(1.0))

    def forward(self, **kwargs):
        bases = kwargs['points']
        encodings = kwargs['encodings']
        uvs = kwargs['uv']

        # TODO: operate on dict of tensors
        X = [ encodings, bases, uvs ]
        for i in range(self.L):
            X += [ torch.sin(2 ** i * uvs), torch.cos(2 ** i * uvs) ]
        X = torch.cat(X, dim=-1)

        for i, linear in enumerate(self.encoding_linears):
            X = linear(X)
            if i < len(self.encoding_linears) - 1:
                # TODO: plot s0, s1, w0, w1 as well
                if i == 0:
                    X = torch.exp(-self.s0 * X ** 2) * torch.sin(self.w0 * X)
                elif i == 1:
                    X = torch.exp(-self.s1 * X ** 2) * torch.sin(self.w1 * X)

        return bases + X

class MLP_UV_Onion_Encoding(nn.Module):
    L = 8

    def __init__(self) -> None:
        super(MLP_UV_Onion_Encoding, self).__init__()

        # Pass configuration as constructor arguments
        self.encoding_linears = [
            nn.Linear((2 * self.L + 1) * 2 + 3 + POINT_ENCODING_SIZE, 64),
            nn.Linear(64, 64),
            nn.Linear(64, 64),
            nn.Linear(64, 3)
        ]

        self.encoding_linears = nn.ModuleList(self.encoding_linears)

        self.s0 = nn.Parameter(torch.tensor(1.0))
        self.s1 = nn.Parameter(torch.tensor(1.0))

    def onion(self, x, s):
        softplus = torch.log(1 + torch.exp(x))
        sin = torch.sin(s * x)
        exp = torch.exp(-s * x ** 2)
        return softplus * sin * exp

    def forward(self, **kwargs):
        bases = kwargs['points']
        encodings = kwargs['encodings']
        uvs = kwargs['uv']

        # TODO: operate on dict of tensors
        X = [ encodings, bases, uvs ]
        for i in range(self.L):
            X += [ torch.sin(2 ** i * uvs), torch.cos(2 ** i * uvs) ]
        X = torch.cat(X, dim=-1)

        for i, linear in enumerate(self.encoding_linears):
            X = linear(X)
            if i < len(self.encoding_linears) - 1:
                X = self.onion(X, self.s0 if i == 0 else self.s1)

        return bases + X

# TODO: UV RBF encoding...
