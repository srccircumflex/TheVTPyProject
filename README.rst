
.. role:: html(raw)
   :format: html


.. .. image:: ./_doc/pics/building_side.png
    :width: 121
    :alt: building_side.png


The [ Video Terminal Python ] Project
#####################################

.. image:: ./_doc/VT-Python-Logo.png
    :align: center
    :width: 550
    :alt: VT-Python-Logo.png

Statute
=======

The goal of the project is to create a comprehensive Python library, for creating text-based user interfaces
in the terminal emulator.

The current build-out includes a module for the Linux/Windows platform independent modification of the
emulator; several modules for categorizing, cataloging, handling, interpreting, and processing data types,
data inputs, and the ANSI escape sequences; a package for technical processing of an unblocked stdin stream;
and the first basic modules and objects for implementing text-based widgets.

The development is done by myself on a hobby basis, the progress and next goals can be seen under
Issues_. There is also full documentation available in the Wiki_.

Reports, ideas and questions are very welcome and can be directed to
:html:`<a href="mailto:srccircumflex@outlook.com?subject=The%20VT-Python%20Project">
srccircumflex@outlook.com</a>`.


Presentations
=============

SGR Lookup
----------

.. image:: ./_doc/gifs/SGRLookup.gif
    :align: center
    :width: 1050
    :alt: SGRLookup.gif

→ `demo sgr_lookup_tui`_

Find in Buffer
--------------

.. image:: ./_doc/gifs/FindInBuffer.gif
    :align: center
    :width: 1050
    :alt: FindInBuffer.gif

→ `demo editor`_

Insert Modes
------------

.. image:: ./_doc/gifs/InsertModes.gif
    :align: center
    :width: 1050
    :alt: InsertModes.gif

→ `demo editor`_

Highlighter Demo
----------------

.. image:: ./_doc/gifs/HighlighterDemo.gif
    :align: center
    :width: 1050
    :alt: HighlighterDemo.gif

Tab Shifting
------------

.. image:: ./_doc/gifs/TabShift.gif
    :align: center
    :width: 1050
    :alt: TabShift.gif

→ `demo editor`_

Markers
-------

.. image:: ./_doc/gifs/Markers.gif
    :align: center
    :width: 1050
    :alt: Markers.gif

→ `demo editor`_


.. _Issues: https://github.com/srccircumflex/TheVTPyProject/issues
.. _Wiki: https://github.com/srccircumflex/TheVTPyProject/wiki

.. _demo editor: ./_demo/editor.py
.. _demo sgr_lookup_tui: ./_demo/sgr_lookup_tui.py
