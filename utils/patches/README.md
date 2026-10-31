# SkinTokens runtime patch provenance

`skintokens-prefill-dtype.patch` is a local Comfy3D compatibility correction,
not an upstream commit or an upstream-endorsed fix. It modifies
`TokenRig.generate` in VAST-AI-Research/SkinTokens at the immutable upstream
commit `273b691d35989d71cd17ff2895fdc735097b92d1`.
Upstream repository: `https://github.com/VAST-AI-Research/SkinTokens.git`.
Upstream copyright: (c) 2025 VAST-AI-Research, MIT license (retained below).

The patch is byte-for-byte the correction exercised in the isolated Spark GB10
worker smoke (`prefill-dtype.patch` in the retained Spark evidence bundle).
SHA256: `85de82bf3f405c015509543100e3ac2a72a605eaf7db731d1fb955a99233b9f7`.

Review scope: only the concatenated prefill embedding is cast to
`start_embed.dtype` before Qwen generation. RMSNorm/autocast can promote mesh
conditioning to fp32; without the cast, the prefill KV cache is fp32 while
subsequent decode queries are bf16, which real FlashAttention rejects.
No weights, training path, attention implementation, or server behavior change.
The accompanying comments explain the dtype invariant.

`prepare` accepts a pristine base or this exact patched tree, applies the patch
only to the pristine base, and verifies again. `validate` requires the patched
tree; it never repairs source. Both reject every other tracked change, including
staged edits and file modes. The expected tree is derived using a temporary Git
index; the user's index and unrelated files are not rewritten. Untracked model
links and inference outputs are allowed, as before. This is tracked-source
integrity validation, not a sandbox against malicious untracked Python files.

See `docs/skintokens.md` for runtime versions, artifact evidence, and limitations.
Requalify the patch before changing the source pin; do not silently skip failed
patch application or globally permit dirty source trees.

## Upstream license

MIT License

Copyright (c) 2025 VAST-AI-Research

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
