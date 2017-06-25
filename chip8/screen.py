from pygame import display, HWSURFACE, DOUBLEBUF, Color, draw

# Various screen modes
SCREEN_MODE_NORMAL = 'normal'
SCREEN_MODE_EXTENDED = 'extended'
SCREEN_NAME = 'CHIP8 Emulator - Project'
# The height of the screen in pixels. Note this may be augmented by the
# scale_factor set by the initializer.
SCREEN_HEIGHT = {
    SCREEN_MODE_NORMAL: 32,
    SCREEN_MODE_EXTENDED: 64
}
DEFAULT_HEIGHT = SCREEN_HEIGHT[SCREEN_MODE_NORMAL]

# The width of the screen in pixels. Note this may be augmented by the
# scale_factor set by the initializer.
SCREEN_WIDTH = {
    SCREEN_MODE_NORMAL: 64,
    SCREEN_MODE_EXTENDED: 128
}
DEFAULT_WIDTH = SCREEN_WIDTH[SCREEN_MODE_NORMAL]

# The depth of the screen is the number of bits used to represent the color
# of a pixel.
SCREEN_DEPTH = 8

# The colors of the pixels to draw. The Chip 8 supports two colors: 0 (off)
# and 1 (on). The format of the colors is in RGBA format.
PIXEL_COLORS = {
    0: Color(0, 0, 0, 255),
    1: Color(250, 250, 250, 255)
}


class Screen(object):
    """
    A class to emulate a Chip 8 Screen. The original Chip 8 screen was 64 x 32
    with 2 colors. In this emulator, this translates to color 0 (off) and color
    1 (on).
    """
    def __init__(self, ratio, screen_height=DEFAULT_HEIGHT, screen_width=DEFAULT_WIDTH):
        """
        Initializes the main screen. The scale factor is used to modify
        the size of the main screen, since the original resolution of the
        Chip 8 was 64 x 32, which is quite small.

        :param scale_factor: the scaling factor to apply to the screen
        :param height: the height of the screen
        :param width: the width of the screen
        """
        self.screen_height = screen_height
        self.screen_width = screen_width
        self.scaling_ratio = ratio
        self.screen_surface = None

    def init_display(self):
        """
        Attempts to initialize a screen with the specified height and width.
        The screen will by default be of depth SCREEN_DEPTH, and will be
        double-buffered in hardware (if possible).
        """
        display.init()
        self.screen_surface = display.set_mode(
            ((self.screen_width * self.scaling_ratio),
             (self.screen_height * self.scaling_ratio)),
            HWSURFACE | DOUBLEBUF,
            SCREEN_DEPTH)
        display.set_caption(SCREEN_NAME)
        self.screen_surface.fill(PIXEL_COLORS[0])
        display.flip()

    def draw_screen_pixel(self, x_axis_position, y_axis_position, pixel_color):
        """
        Turn a pixel on or off at the specified location on the screen. Note
        that the pixel will not automatically be drawn on the screen, you
        must call the update() function to flip the drawing buffer to the
        display. The coordinate system starts with (0, 0) being in the top
        left of the screen.

        :param x_pos: the x coordinate to place the pixel
        :param y_pos: the y coordinate to place the pixel
        :param pixel_color: the color of the pixel to draw
        """
        x_axis_base_position = x_axis_position * self.scaling_ratio
        y_axis_base_position = y_axis_position * self.scaling_ratio
        draw.rect(self.screen_surface,
                  PIXEL_COLORS[pixel_color],
                  (x_axis_base_position, y_axis_base_position, self.scaling_ratio, self.scaling_ratio))

    def get_screen_pixel(self, x_axis_position, y_axis_position):
        """
        Returns whether the pixel is on (1) or off (0) at the specified
        location.

        :param x_pos: the x coordinate to check
        :param y_pos: the y coordinate to check
        :return: the color of the specified pixel (0 or 1)
        """
        x_axis_scaled_position = x_axis_position * self.scaling_ratio
        y_axis_scaled_position = y_axis_position * self.scaling_ratio
        pixel_color = self.screen_surface.get_at((x_axis_scaled_position, y_axis_scaled_position))
        if pixel_color == PIXEL_COLORS[0]:
            color = 0
        else:
            color = 1
        return color

    def clear_screen(self):
        """
        Turns off all the pixels on the screen (writes color 0 to all pixels).
        """
        self.screen_surface.fill(PIXEL_COLORS[0])

    @staticmethod
    def update_screen():
        """
        Updates the display by swapping the back buffer and screen buffer.
        According to the pygame documentation, the flip should wait for a
        vertical retrace when both HWSURFACE and DOUBLEBUF are set on the
        surface.
        """
        display.flip()

    def set_screen_extended(self):
        """
        Sets the screen mode to extended.
        """
        display.quit()
        self.screen_height = SCREEN_HEIGHT[SCREEN_MODE_EXTENDED]
        self.screen_width = SCREEN_WIDTH[SCREEN_MODE_EXTENDED]
        self.init_display()

    def set_screen_normal(self):
        """
        Sets the screen mode to normal.
        """
        display.quit()
        self.screen_height = SCREEN_HEIGHT[SCREEN_MODE_NORMAL]
        self.screen_width = SCREEN_WIDTH[SCREEN_MODE_NORMAL]
        self.init_display()

    def scroll_screen_down(self, line_number_count):
        """
        Scroll the screen down by num_lines.
        
        :param num_lines: the number of lines to scroll down 
        """
        for y_axis_position in xrange(self.screen_height - line_number_count, -1, -1):
            for x_axis_position in xrange(self.screen_width):
                pixel_color = self.get_pixel(x_axis_position, y_axis_position)
                self.draw_pixel(x_axis_position, y_axis_position + line_number_count, pixel_color)

        # Blank out the lines above the ones we scrolled
        for y_axis_position in xrange(line_number_count):
            for x_axis_position in xrange(self.screen_width):
                self.draw_pixel(x_axis_position, y_axis_position, 0)

        display.flip()

    def scroll_screen_left(self):
        """
        Scroll the screen left 4 pixels.
        """
        for y_axis_position in xrange(self.screen_height):
            for x_axis_position in xrange(4, self.screen_width):
                pixel_color = self.get_pixel(x_axis_position, y_axis_position)
                self.draw_pixel(x_axis_position - 4, y_axis_position, pixel_color)

        # Blank out the lines to the right of the ones we just scrolled
        for y_axis_position in xrange(self.screen_height):
            for x_axis_position in xrange(self.screen_width - 4, self.screen_width):
                self.draw_pixel(x_axis_position, y_axis_position, 0)

        display.flip()

    def scroll_screen_right(self):
        """
        Scroll the screen right 4 pixels.
        """
        for y_axis_position in xrange(self.screen_height):
            for x_axis_position in xrange(self.screen_width - 4, -1, -1):
                pixel_color = self.get_pixel(x_axis_position, y_axis_position)
                self.draw_pixel(x_axis_position + 4, y_axis_position, pixel_color)

        # Blank out the lines to the left of the ones we just scrolled
        for y_axis_position in xrange(self.screen_height):
            for x_axis_position in xrange(4):
                self.draw_pixel(x_axis_position, y_axis_position, 0)

        display.flip()
