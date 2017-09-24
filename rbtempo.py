# rbtempo: plugin to control Rhythmbox playback speed
# Copyright (C) 2015  Bruce Merry <bmerry@users.sourceforge.net>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from gi.repository import GObject, GLib, Gio, Gtk, RB, Peas, Gst

def find_widget_by_names(root, names):
    """Recursively find the widget whose name is in `names` under root, returning
    `None` if it could not be found."""
    if Gtk.Buildable.get_name(root) in names:
        return root
    if isinstance(root, Gtk.Container):
        for child in root.get_children():
            ans = find_widget_by_names(child, names)
            if ans is not None:
                return ans
    return None

class RBTempoPlugin(GObject.Object, Peas.Activatable):
    object = GObject.property(type=GObject.GObject)

    def get_shell(self):
        return self.object

    def get_player(self):
        return self.get_shell().props.shell_player.props.player

    def get_toolbar(self):
        """Get the widget for the main toolbar."""
        # Detect the rhythymbox "Alternative Toolbar" plugin's toolbar as well as the normal toolbar
        return find_widget_by_names(self.get_shell().props.window, ['small bar', 'main-toolbar'])

    def set_pitch(self):
        self.speed_element.props.pitch = self.speed_adj.get_value() * 0.01 + 1.0

    def set_tempo(self):
        self.speed_element.props.tempo = self.speed_adj.get_value() * 0.01 + 1.0

    def speed_changed(self, x):
        # Convert delta percent to scale value
        if self.speed_adj.get_value() != 0:
            self.add_filter()
        if self.pitch_enabled:
            self.set_pitch()
        if self.tempo_enabled:
            self.set_tempo()

    def create_speed_adj(self):
        self.speed_adj = Gtk.Adjustment(value=0, lower=-50, upper=300, step_increment=5, page_increment=10)
        self.speed_adj.connect('value-changed', self.speed_changed)

    def create_speed_scale(self, adj):
        scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL)
        scale.set_adjustment(adj)
        scale.set_size_request(100, -1)
        scale.set_draw_value(False)
        return scale

    def create_speed_spin(self, adj):
        spin = Gtk.SpinButton.new(adj, 0, 0)
        spin.set_width_chars(4)
        return spin

    def reset(self, button):
        self.remove_filter()
        self.speed_adj.set_value(0)

    def create_reset_button(self):
        reset_button = Gtk.Button.new_from_icon_name('edit-undo', 3)
        reset_button.connect('clicked', self.reset)
        reset_button.show()
        return reset_button

    def pitch_toggled(self, x):
        self.pitch_enabled = not self.pitch_enabled
        if (self.pitch_enabled):
            self.set_pitch()
        else:
            self.speed_element.props.pitch = 1

    def tempo_toggled(self, x):
        self.tempo_enabled = not self.tempo_enabled
        if (self.tempo_enabled):
            self.set_tempo()
        else:
            self.speed_element.props.tempo = 1

    def create_toolbox(self):
        self.create_speed_adj()
        outer_box = Gtk.Box.new(Gtk.Orientation.VERTICAL, 3)
        controls_box = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 3)
        checks_box = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 3)

        pitch_toggle = Gtk.CheckButton.new_with_label('Pitch')
        pitch_toggle.set_active(self.pitch_enabled)
        pitch_toggle.connect('toggled', self.pitch_toggled)

        tempo_toggle = Gtk.CheckButton.new_with_label('Tempo')
        tempo_toggle.set_active(self.tempo_enabled)
        tempo_toggle.connect('toggled', self.tempo_toggled)

        controls_box.pack_start(self.create_speed_scale(self.speed_adj), True, True, 0)
        controls_box.pack_start(self.create_speed_spin(self.speed_adj), False, False, 0)
        controls_box.pack_start(self.create_reset_button(), False, False, 0)

        checks_box.pack_start(pitch_toggle, False, False, 0)
        checks_box.pack_start(tempo_toggle, False, False, 0)

        outer_box.pack_start(controls_box, False, False, 0)
        outer_box.pack_start(checks_box, True, True, 0)

        item = Gtk.ToolItem.new()
        item.set_margin_left(6)

        button = Gtk.ToggleButton.new()
        button.set_image(Gtk.Image.new_from_icon_name('media-seek-forward', 4))

        popover = Gtk.Popover.new(button)
        popover.set_modal(False)
        popover.add(outer_box)

        button.connect('clicked', self.showhide, popover)
        item.add(button)
        item.show_all()
        return item

    def showhide(self, x, a):
        self.open = not self.open
        if self.open:
            a.show_all()
        else:
            a.hide()

    def add_filter(self):
        """Add the filter to the player, if not already present"""
        if self.speed_element is None:
            self.speed_element = Gst.ElementFactory.make("pitch", None)
            self.get_player().add_filter(self.speed_element)

    def remove_filter(self):
        """Delete the filter if it is present"""
        if self.speed_element is not None:
            self.get_player().remove_filter(self.speed_element)
            self.speed_element = None

    def do_activate(self):
        """Plugin activation callback"""
        Gst.init([])     # Workaround for https://bugzilla.gnome.org/show_bug.cgi?id=788088
        self.pitch_enabled = True
        self.tempo_enabled = True
        self.open = False
        self.speed_element = None
        self.toolbox = self.create_toolbox()
        self.toolbar = self.get_toolbar()
        if self.toolbar is not None:
            self.toolbar.insert(self.toolbox, 2)

    def do_deactivate(self):
        """Plugin deactivation callback"""
        if self.toolbar is not None:
            self.toolbar.remove(self.toolbox)
        self.remove_filter()
        del self.toolbox
        del self.speed_element
