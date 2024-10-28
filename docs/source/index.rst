.. podcastfy documentation master file, created by
   sphinx-quickstart on Sat Oct 12 21:09:23 2024.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Podcastfy.ai API Referece Manual
==========================

This documentation site is focused on the Podcastfy Python package, its classes, functions, and methods.
For additional documentation, see the `Podcastfy <https://github.com/souzatharsis/podcastfy/>`_ GitHub repository.
       
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

- `Python Package <https://github.com/souzatharsis/podcastfy/blob/main/podcastfy.ipynb>`_

- `CLI <https://github.com/souzatharsis/podcastfy/blob/main/usage/cli.md>`_

Experience Podcastfy with our `HuggingFace <https://huggingface.co/spaces/thatupiso/Podcastfy.ai_demo>`_ 🤗 Spaces app for a simple URL-to-Audio demo. (Note: This UI app is less extensively tested and capable than the Python package.)

Customization
-------------

Podcastfy offers a range of customization options to tailor your AI-generated podcasts:

* Customize podcast `Conversation <https://github.com/souzatharsis/podcastfy/blob/main/usage/conversation_custom.md>`_ (e.g. format, style)
* Choose to run `Local LLMs <https://github.com/souzatharsis/podcastfy/blob/main/usage/local_llm.md>`_ (156+ HuggingFace models)
* Set `System Settings <https://github.com/souzatharsis/podcastfy/blob/main/usage/config_custom.md>`_ (e.g. text-to-speech and output directory settings)


Collaborate
===========

Fork me at https://github.com/souzatharsis/podcastfy.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

Licensed under Apache 2.0
