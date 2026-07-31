PoreScene
=========

PoreScene is a `Blender <https://docs.blender.org/api/current/>`_-based scientific
visualization toolkit for porous media. It renders tomographic images, generated and
reconstructed pore networks, as well as volume tessellations as photorealistic 3D scenes
-- with pores, throats, Voronoi cells, and watershed clusters colored by quantities such
as radius or coordination number using perceptually uniform colormaps, matching
colorbars, and calibrated, on-scale axes.

The advantage: instead of clicking through a 3D editor, you describe the entire scene in a
few lines of Python and render it reproducibly on Blender's GPU-accelerated *Cycles*
engine -- so the same script always yields the same publication-quality figure, ready for
papers, presentations, and animations.

.. carousel::
   :interval: 2500
   :copyright: Felix Faber / OVGU, Transport in Porous Media

   .. figure:: /_static/image/carousel/startpage/slide-0.png

      Microstructure of a freeze-dried sugar solution.

   .. figure:: /_static/image/carousel/startpage/slide-1.png

      Pore and throat morphology of a reconstructed pore network.

   .. figure:: /_static/image/carousel/startpage/slide-2.png

      Simulated lactate concentration during biofilm growth.

   .. figure:: /_static/image/carousel/startpage/slide-3.png
      :alt: PNM stick and ball representation

      Pore space tessellation of a reconstructed X-ray µ-CT image of a rock.

   .. figure:: /_static/image/carousel/startpage/slide-4.png
      :alt: Pore coordination numbers

      Microstructure of a graded titanium felt used in PEM water electrolyzers.

   .. figure:: /_static/image/carousel/startpage/slide-5.png

      Oxygen concentration during Fickian diffusion.

   .. figure:: /_static/image/carousel/startpage/slide-6.png

      Pore coordination numbers of a reconstructed pore network from wood.

   .. figure:: /_static/image/carousel/startpage/slide-7.png

      Pore clusters of a regular pore network.

   .. figure:: /_static/image/carousel/startpage/slide-8.png

      Ice saturation in the pore space during freeze-drying.

   .. figure:: /_static/image/carousel/startpage/slide-9.png

      Structure of an *in-silico* computed biofilm.

   .. figure:: /_static/image/carousel/startpage/slide-10.png

      Pore and throat diameters of a regular pore network.

   .. figure:: /_static/image/carousel/startpage/slide-11.png

      Packed bed of monodisperse alumina spheres.

   .. figure:: /_static/image/carousel/startpage/slide-12.png

      Microstructure of a European beech wood sphere.

Navigation
----------

.. raw:: html

   <div class="ps-tiles">
     <a class="ps-tile clickable" href="installation.html">
       <svg class="ps-tile-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
         <path d="M12 3v12"/>
         <path d="m7 10 5 5 5-5"/>
         <path d="M4 19h16"/>
       </svg>
       <h3 class="ps-tile-title">Installation</h3>
       <p class="ps-tile-desc">Set up PoreScene and its Blender-based rendering pipeline.</p>
     </a>
     <a class="ps-tile clickable" href="concepts.html">
       <svg class="ps-tile-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
         <circle cx="12" cy="12" r="10"/>
         <polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/>
       </svg>
       <h3 class="ps-tile-title">Concepts</h3>
       <p class="ps-tile-desc">Coordinate axes, units, and how scenes are composed from components.</p>
     </a>
     <a class="ps-tile clickable" href="examples.html">
       <svg class="ps-tile-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
         <rect x="3" y="4" width="18" height="14" rx="2"/>
         <circle cx="8.5" cy="9.5" r="1.5"/>
         <path d="m4 16 4.5-4.5a2 2 0 0 1 2.8 0L17 17"/>
       </svg>
       <h3 class="ps-tile-title">Examples</h3>
       <p class="ps-tile-desc">Annotated scripts showing how to build and render scenes.</p>
     </a>
     <a class="ps-tile clickable" href="api/porescene.html">
       <svg class="ps-tile-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
         <path d="m8 6-5 6 5 6"/>
         <path d="m16 6 5 6-5 6"/>
       </svg>
       <h3 class="ps-tile-title">API Reference</h3>
       <p class="ps-tile-desc">Browse the full module, class, and function documentation.</p>
     </a>
     <a class="ps-tile clickable" href="publications.html">
       <svg class="ps-tile-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
         <path d="M12 7v14"/>
         <path d="M3 18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4 4 4 0 0 1 4-4h5a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-6a3 3 0 0 0-3 3 3 3 0 0 0-3-3z"/>
       </svg>
       <h3 class="ps-tile-title">Publications</h3>
       <p class="ps-tile-desc">Papers featuring visualizations created with PoreScene.</p>
     </a>
     <a class="ps-tile clickable" href="https://github.com/fefafe/porescene" target="_blank" rel="noopener noreferrer">
       <svg class="ps-tile-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
         <line x1="6" y1="3" x2="6" y2="15"/>
         <circle cx="18" cy="6" r="3"/>
         <circle cx="6" cy="18" r="3"/>
         <path d="M18 9a9 9 0 0 1-9 9"/>
       </svg>
       <h3 class="ps-tile-title">Repository</h3>
       <p class="ps-tile-desc">Browse the source, report issues, and contribute on GitHub.</p>
     </a>
   </div>

.. toctree::
   :maxdepth: 2
   :caption: Getting Started
   :hidden:

   installation
   concepts
   config
   examples

.. toctree::
   :maxdepth: 2
   :caption: API Reference
   :hidden:

   api/porescene

.. toctree::
   :maxdepth: 2
   :caption: Publications
   :hidden:

   publications

Citation
--------

If you use PoreScene to generate figures for a publication, please cite it. Citation
metadata is provided in the repository's ``CITATION.cff``, and the software is archived on
Zenodo under a version-independent concept
`DOI <https://doi.org/10.5281/zenodo.21494378>`_ that always resolves to the latest
release. You can use the BibTeX entry below:

.. code-block:: bibtex

   @software{porescene,
     author = {Faber, Felix and Vorhauer-Huget, Nicole},
     title  = {{PoreScene}},
     year   = {2026},
     doi    = {10.5281/zenodo.21494378},
     url    = {https://github.com/fefafe/porescene},
   }

Creators
--------

.. raw:: html

   <div class="ps-tiles">
     <div class="ps-tile non-clickable">
       <p class="ps-tile-title">Felix Faber</p>
       <p class="ps-tile-subtitle">Creator &amp; maintainer of PoreScene</p>
       <p class="ps-tile-desc">
       <a class="ps-author-orcid" href="https://orcid.org/0009-0004-4860-9269" target="_blank" rel="noopener noreferrer">
         <svg viewBox="0 0 256 256" xmlns="http://www.w3.org/2000/svg" aria-hidden="true" class="inline-icon">
           <path fill="#A6CE39" d="M256,128c0,70.7-57.3,128-128,128C57.3,256,0,198.7,0,128C0,57.3,57.3,0,128,0C198.7,0,256,57.3,256,128z"/>
           <path fill="#FFFFFF" d="M86.3,186.2H70.9V79.1h15.4v48.4V186.2z"/>
           <path fill="#FFFFFF" d="M108.9,79.1h41.6c39.6,0,57,28.3,57,53.6c0,27.5-21.5,53.6-56.8,53.6h-41.8V79.1z M124.3,172.4h24.5c34.9,0,42.9-26.5,42.9-39.7c0-21.5-13.7-39.7-43.7-39.7h-23.7V172.4z"/>
           <path fill="#FFFFFF" d="M88.7,56.8c0,5.5-4.5,10.1-10.1,10.1c-5.6,0-10.1-4.6-10.1-10.1c0-5.6,4.5-10.1,10.1-10.1C84.2,46.7,88.7,51.3,88.7,56.8z"/>
         </svg>
         <span>0009-0004-4860-9269</span>
       </a></p>
       <p class="ps-tile-desc">
       <a class="ps-author-email" href="mailto:felix.faber@ovgu.de">
         <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" class="inline-icon">
           <rect x="3" y="5" width="18" height="14" rx="2"/>
           <path d="m3 7 9 6 9-6"/>
         </svg>
         <span>felix.faber@ovgu.de</span>
       </a></p>
     </div>

     <div class="ps-tile non-clickable">
       <p class="ps-tile-title">Nicole Vorhauer-Huget</p>
       <p class="ps-tile-subtitle">Research group leader <a href="https://tvt.ovgu.de/tpm" target="_blank" rel="noopener noreferrer">Transport in Porous Media</a> at <a href="https://ovgu.de/" target="_blank" rel="noopener noreferrer">OVGU</a></p>
       <p class="ps-tile-desc">
        <a class="ps-author-orcid" href="https://orcid.org/0000-0001-5825-4984" target="_blank" rel="noopener noreferrer">
          <svg viewBox="0 0 256 256" xmlns="http://www.w3.org/2000/svg" aria-hidden="true" class="inline-icon">
            <path fill="#A6CE39" d="M256,128c0,70.7-57.3,128-128,128C57.3,256,0,198.7,0,128C0,57.3,57.3,0,128,0C198.7,0,256,57.3,256,128z"/>
            <path fill="#FFFFFF" d="M86.3,186.2H70.9V79.1h15.4v48.4V186.2z"/>
            <path fill="#FFFFFF" d="M108.9,79.1h41.6c39.6,0,57,28.3,57,53.6c0,27.5-21.5,53.6-56.8,53.6h-41.8V79.1z M124.3,172.4h24.5c34.9,0,42.9-26.5,42.9-39.7c0-21.5-13.7-39.7-43.7-39.7h-23.7V172.4z"/>
            <path fill="#FFFFFF" d="M88.7,56.8c0,5.5-4.5,10.1-10.1,10.1c-5.6,0-10.1-4.6-10.1-10.1c0-5.6,4.5-10.1,10.1-10.1C84.2,46.7,88.7,51.3,88.7,56.8z"/>
          </svg>
          <span>0000-0001-5825-4984</span>
        </a>
       </p>
       <p class="ps-tile-desc">
       <a class="ps-author-email" href="mailto:nicole.vorhauer-huget@ovgu.de">
         <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" class="inline-icon">
           <rect x="3" y="5" width="18" height="14" rx="2"/>
           <path d="m3 7 9 6 9-6"/>
         </svg>
         <span>nicole.vorhauer-huget@ovgu.de</span>
       </a></a>
     </div>
   </div>


Funding
-------

.. raw:: html

   <div class="ps-tiles">
     <div class="ps-tile non-clickable">
       <p class="ps-tile-title">CRC 287 Bulk-Reaction</p>
       <p class="ps-tile-subtitle">This work was funded by the Deutsche Forschungsgemeinschaft (DFG, German Research Foundation) – Project-ID 422037413 – TRR 287 "<a href="https://bulk-reaction.de/" target="_blank" rel="noopener noreferrer">Bulk-Reaction</a>".</p>
     </div>
   </div>
