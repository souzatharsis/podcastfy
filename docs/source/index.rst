.. podcastfy documentation master file, created by
   sphinx-quickstart on Sat Oct 12 21:09:23 2024.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Podcastfy.ai documentation
==========================

Transforming Multimodal Content into Captivating Multilingual Audio Conversations with GenAI
   
.. toctree::
   :maxdepth: 3
   :caption: User Documentation:
   
   podcastfy_demo.ipynb
       
.. toctree::
   :maxdepth: 2
   :caption: API Reference:
   
   podcastfy


Quickstart
----------

Prerequisites
^^^^^^^^^^^^^
- Python 3.11 or higher
- ``$ pip install ffmpeg`` (for audio processing)

Installation
^^^^^^^^^^^^
1. Install from PyPI:
   
   ``$ pip install podcastfy``

2. Set up your `API keys <https://github.com/souzatharsis/podcastfy/blob/main/usage/config.md>`_

Python
^^^^^^
.. code-block:: python

   from podcastfy.client import generate_podcast

   audio_file = generate_podcast(urls=["<url1>", "<url2>"])

CLI
^^^
.. code-block:: bash

   python -m podcastfy.client --url <url1> --url <url2>

Usage
-----

- `Python Package <podcastfy.ipynb>`_

- `CLI <https://github.com/souzatharsis/podcastfy/blob/main/usage/cli.md>`_

Experience Podcastfy with our `HuggingFace <https://huggingface.co/spaces/thatupiso/Podcastfy.ai_demo>`_ 🤗 Spaces app for a simple URL-to-Audio demo. (Note: This UI app is less extensively tested than the Python package.)

Customization
-------------

Podcastfy offers a range of `Conversation Customization <https://github.com/souzatharsis/podcastfy/blob/main/usage/conversation_custom.md>`_ options to tailor your AI-generated podcasts. Whether you're creating educational content, storytelling experiences, or anything in between, these configuration options allow you to fine-tune your podcast's tone, length, and format.


Collaborate
===========

Fork me at https://github.com/souzatharsis/podcastfy.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

Licensed under Attribution-NonCommercial-ShareAlike 4.0 International.
