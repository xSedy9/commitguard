# Support

## How to Get Help

If you run into issues or have questions about commitguard:

1. **Documentation**:
   - Check [README.md](README.md) for installation and provider configuration.
   - Check [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for full architectural details.
2. **Issues**:
   - If you encounter a bug or unexpected behavior, open an issue on GitHub with reproduction steps.
   - For security-sensitive issues, refer to [SECURITY.md](SECURITY.md).
3. **Common Troubleshooting**:
   - **Bypass warning**: `--no-verify` is deliberately stripped. Fix the underlying issues to commit.
   - **AI timeout**: commitguard fails open if the AI provider times out, so your commits are never blocked by network latency.
   - **CI pipelines**: pass `--commitguard-no-ai` to run Layer 1 checks without requiring API keys.
