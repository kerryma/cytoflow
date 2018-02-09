#!/usr/bin/env python3.4
# coding: latin-1

# (c) Massachusetts Institute of Technology 2015-2017
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

'''
Density Plot
------------

Plots a 2-dimensional density plot.

.. object:: X Channel, Y Channel

    The channels to plot on the X and Y axes.
    
.. object:: X Scale, Y Scale

    How to scale the X and Y axes of the plot.
    
.. object:: Horizonal Facet

    Make multiple plots.  Each column has a unique value of this variable.
    
.. object:: Vertical Facet

    Make multiple plots.  Each row has a unique value of this variable.

.. object:: Color Scale

    Scale the color palette and the color bar
    
.. object:: Tab Facet

    Make multiple plots in differen tabs; each tab's plot has a unique value
    of this variable.
    
.. object:: Subset

    Plot only a subset of the data in the experiment.
    
.. plot::
        
    import cytoflow as flow
    import_op = flow.ImportOp()
    import_op.tubes = [flow.Tube(file = "Plate01/RFP_Well_A3.fcs",
                                 conditions = {'Dox' : 10.0}),
                       flow.Tube(file = "Plate01/CFP_Well_A4.fcs",
                                 conditions = {'Dox' : 1.0})]
    import_op.conditions = {'Dox' : 'float'}
    ex = import_op.apply()

    flow.DensityView(xchannel = 'V2-A',
                     xscale = 'log',
                     ychannel = 'Y2-A',
                     yscale = 'log').plot(ex)

'''

from traits.api import provides, Callable, Str
from traitsui.api import View, Item, Controller, EnumEditor, VGroup
from envisage.api import Plugin, contributes_to
from pyface.api import ImageResource

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from cytoflow import DensityView
import cytoflow.utility as util

from cytoflowgui.subset import SubsetListEditor
from cytoflowgui.ext_enum_editor import ExtendableEnumEditor
from cytoflowgui.color_text_editor import ColorTextEditor
from cytoflowgui.view_plugins.i_view_plugin \
    import IViewPlugin, VIEW_PLUGIN_EXT, ViewHandlerMixin, PluginViewMixin, PluginHelpMixin
from cytoflowgui.serialization import camel_registry, traits_repr, dedent
from cytoflowgui.util import IterWrapper

DensityView.__repr__ = traits_repr

class DensityHandler(ViewHandlerMixin, Controller):

    def default_traits_view(self):
        return View(VGroup(
                    VGroup(Item('xchannel',
                                editor=EnumEditor(name='context.channels'),
                                label = "X Channel"),
                           Item('xscale',
                                label = "X Scale"),
                           Item('ychannel',
                                editor=EnumEditor(name='context.channels'),
                                label = "Y Channel"),
                           Item('yscale',
                                label = "Y Scale"),
                           Item('xfacet',
                                editor=ExtendableEnumEditor(name='handler.conditions_names',
                                                            extra_items = {"None" : ""}),
                                label = "Horizontal\nFacet"),
                           Item('yfacet',
                                editor=ExtendableEnumEditor(name='handler.conditions_names',
                                                            extra_items = {"None" : ""}),
                                label = "Vertical\nFacet"),
                           Item('huescale',
                                label = "Color\nScale"),
                           Item('plotfacet',
                                editor=ExtendableEnumEditor(name='handler.conditions_names',
                                                            extra_items = {"None" : ""}),
                                label = "Tab\nFacet"),
                           label = "2D Histogram",
                           show_border = False),
                    VGroup(Item('subset_list',
                                show_label = False,
                                editor = SubsetListEditor(conditions = "context.conditions")),
                           label = "Subset",
                           show_border = False,
                           show_labels = False),
                    Item('context.view_warning',
                         resizable = True,
                         visible_when = 'context.view_warning',
                         editor = ColorTextEditor(foreground_color = "#000000",
                                                 background_color = "#ffff99")),
                    Item('context.view_error',
                         resizable = True,
                         visible_when = 'context.view_error',
                         editor = ColorTextEditor(foreground_color = "#000000",
                                                  background_color = "#ff9191"))))

class DensityPluginView(PluginViewMixin, DensityView):
    handler_factory = Callable(DensityHandler)
    plotfacet = Str

    def enum_plots_wi(self, wi):
        if not self.plotfacet:
            return iter([])
        
        if self.plotfacet and self.plotfacet not in wi.result.conditions:
            raise util.CytoflowViewError("Plot facet {0} not in the experiment"
                                    .format(self.huefacet))
        values = np.sort(pd.unique(wi.result[self.plotfacet]))
        return IterWrapper(iter(values), [self.plotfacet])

    
    def plot(self, experiment, plot_name = None, **kwargs):
        
        if experiment is None:
            raise util.CytoflowViewError("No experiment specified")
        
        if self.plotfacet and plot_name is not None:
            experiment = experiment.subset(self.plotfacet, plot_name)

        DensityView.plot(self, experiment, **kwargs)
        
        if self.plotfacet and plot_name is not None:
            plt.title("{0} = {1}".format(self.plotfacet, plot_name))
            
    def get_notebook_code(self, idx):
        view = DensityView()
        view.copy_traits(self, view.copyable_trait_names())

        return dedent("""
        {repr}.plot(ex_{idx}{plot})
        """
        .format(repr = repr(view),
                idx = idx,
                plot = ", plot_name = " + repr(self.current_plot) if self.plot_names else ""))

@provides(IViewPlugin)
class DensityPlugin(Plugin, PluginHelpMixin):

    id = 'edu.mit.synbio.cytoflowgui.view.density'
    view_id = 'edu.mit.synbio.cytoflow.view.density'
    short_name = "Density Plot"

    def get_view(self):
        return DensityPluginView()
    
    def get_icon(self):
        return ImageResource('density')

    @contributes_to(VIEW_PLUGIN_EXT)
    def get_plugin(self):
        return self
        
### Serialization
@camel_registry.dumper(DensityPluginView, 'density-view', version = 1)
def _dump(view):
    return dict(xchannel = view.xchannel,
                xscale = view.xscale,
                ychannel = view.ychannel,
                yscale = view.yscale,
                xfacet = view.xfacet,
                yfacet = view.yfacet,
                huescale = view.huescale,
                plotfacet = view.plotfacet,
                subset_list = view.subset_list)
    
@camel_registry.loader('density-view', version = 1)
def _load(data, version):
    return DensityPluginView(**data)