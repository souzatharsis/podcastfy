# Local LLM Support

Running local LLMs can offer several advantages such as:
- Enhanced privacy and data security
- Cost control and no API rate limits
- Greater customization and fine-tuning options
- Reduced vendor lock-in

We enable serving local LLMs with [llamafile](https://github.com/Mozilla-Ocho/llamafile). In the API, local LLM support is available through the `is_local` parameter. If `is_local=True`, then a local (llamafile) LLM model is used to generate the podcast transcript. Llamafiles of LLM models can be found on [HuggingFace, which today offers 156+ models](https://huggingface.co/models?library=llamafile).

All you need to do is:

1. Download a llamafile from HuggingFace
2. Make the file executable
3. Run the file

Here's a simple bash script that shows all 3 setup steps for running TinyLlama-1.1B locally:

```bash
# Download a llamafile from HuggingFace
wget https://huggingface.co/jartine/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/TinyLlama-1.1B-Chat-v1.0.Q5_K_M.llamafile

# Make the file executable. On Windows, instead just rename the file to end in ".exe".
chmod +x TinyLlama-1.1B-Chat-v1.0.Q5_K_M.llamafile

# Start the model server. Listens at http://localhost:8080 by default.
./TinyLlama-1.1B-Chat-v1.0.Q5_K_M.llamafile --server --nobrowser
```

Now you can use the local LLM to generate a podcast transcript (or audio) by setting the `is_local` parameter to `True`.

## Python API

```python
from podcastfy import generate_podcast

# Generate a tech debate podcast about artificial intelligence
generate_podcast(
    urls=["www.souzatharsis.com"],
    is_local=True  # Using a local LLM
)
```

## CLI

To use a local LLM model via the command-line interface, you can use the `--local` or `-l` flag. Here's an example of how to generate a transcript using a local LLM:

```bash
python -m podcastfy.client --url https://example.com/article1 --transcript-only --local
```

## Notes of caution

When using local LLM models versus widely known private large language models:

1. Performance: Local LLMs often have lower performance compared to large private models due to size and training limitations.

2. Resource requirements: Running local LLMs can be computationally intensive, requiring significant CPU/GPU resources.

3. Limited capabilities: Local models may struggle with complex tasks or specialized knowledge that larger models handle well.

5. Reduced multimodal abilities: Local LLMs will be assumed to be text-only capable

6. Potential instability: Local models may produce less consistent or stable outputs compared to well-tested private models oftentimes producing transcripts that cannot be used for podcast generation (TTS) out-of-the-box

7. Limited context window: Local models often have smaller context windows, limiting their ability to process long inputs.

Always evaluate the trade-offs between using local LLMs and private models based on your specific use case and requirements. We highly recommend extensively testing your local LLM before productionizing an end-to-end podcast generation and/or manually checking the transcript before passing to TTS model.
