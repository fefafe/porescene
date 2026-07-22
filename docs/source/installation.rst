Installation
============

PoreScene is distributed via `PyPI <https://pypi.org/project/porescene/>`_. The
recommended way to install it is with `uv <https://docs.astral.sh/uv/>`_ -- a
fast, cross-platform (Windows, macOS and Linux) package and project manager that
can also download and manage Python interpreters for you.

.. note::

   The supported Python version is restricted by Blender's `bpy
   <https://docs.blender.org/api/current/index.html>`_ module, which is
   **Python 3.13** at the moment. uv provides this interpreter on demand, so you
   do not need a system-wide Python installation.


Quick setup
-----------

If ``uv`` is already available on your system, create a new directory, open your terminal
and create a new virtual environment with Python 3.13,

.. code-block:: text

   uv venv --python 3.13

and add  ``porescene`` to it:

.. code-block:: text

   uv pip install porescene

If you do not have uv yet, follow the step-by-step setup below.


Step-by-step setup
------------------

1. Install uv
^^^^^^^^^^^^^

Install ``uv`` with the official standalone installer.

On **Windows** (PowerShell):

.. code-block:: text

   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

On **macOS** and **Linux**:

.. code-block:: text

   curl -LsSf https://astral.sh/uv/install.sh | sh

Restart your terminal afterwards and verify the installation (all: Windows, macOS, Linux):

.. code-block:: text

   uv --version

.. tip::

   ``uv`` is also available from common package managers, e.g. Homebrew
   (``brew install uv``) or WinGet (``winget install astral-sh.uv``). See the
   `uv installation guide
   <https://docs.astral.sh/uv/getting-started/installation/>`_ for all options.


2. Set up a project
^^^^^^^^^^^^^^^^^^^

Create a new directory an initialize a new virtual environment pinned to Python 3.13.
``uv`` downloads the interpreter if it is not present yet and manages a virtual
environment and dependencies for you:

.. code-block:: text

   uv venv --python 3.13


3. Install PoreScene
^^^^^^^^^^^^^^^^^^^^

Add ``porescene`` to the virtual environment:

.. code-block:: text

   uv pip install porescene

Now, you are ready to create impressive visualizations with PoreScene. See the next chapter for the `basic concepts <concepts.html>`_ of PoreScene, or create your first rendering directly based on of the `example scripts <examples.html>`_.
