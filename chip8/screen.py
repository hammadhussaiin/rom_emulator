from pygame import display, HWSURFACE, DOUBLEBUF, Color, draw

SCREEN_MODE_NORMAL = 'normal'
SCREEN_MODE_EXTENDED = 'extended'
SCREEN_NAME = 'CHIP8 Emulator - Project'
SCREEN_HEIGHT = {
    SCREEN_MODE_NORMAL: 32,
    SCREEN_MODE_EXTENDED: 64
}
DEFAULT_HEIGHT = SCREEN_HEIGHT[SCREEN_MODE_NORMAL]

SCREEN_WIDTH = {
    SCREEN_MODE_NORMAL: 64,
    SCREEN_MODE_EXTENDED: 128
}
DEFAULT_WIDTH = SCREEN_WIDTH[SCREEN_MODE_NORMAL]

SCREEN_DEPTH = 8

PIXEL_COLORS = {
    0: Color(0, 0, 0, 255),
    1: Color(250, 250, 250, 255)
}


class Screen(object):
    """
    Class the imitate the behavior of a Chip-8 Screen.
    """
    def __init__(self, ratio, screen_height=DEFAULT_HEIGHT, screen_width=DEFAULT_WIDTH):
        """
        Class Screen constructor. It initializes the Screen based on the scaling factor
        give as the ratio parameter.

        :param ratio: the scaling factor to apply to the screen
        :param screen_height: the height of the screen
        :param screen_width: the width of the screen
        """
        self.screen_height = screen_height
        self.screen_width = screen_width
        self.scaling_ratio = ratio
        self.screen_surface = None

    def init_display(self):
        """
        This method initializes screen with the height and width
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
        This methods sets the value in the pixel color param for the
        pixel at the x and y coordinates given in the params(if it doesnt
        exist, it will be added.)

        :param x_axis_position: the X coordinate of the pixel
        :param y_axis_position: the Y coordinate of the pixel
        :param pixel_color: the color of the pixel to set/draw
        """
        x_axis_base_position = x_axis_position * self.scaling_ratio
        y_axis_base_position = y_axis_position * self.scaling_ratio
        draw.rect(self.screen_surface,
                  PIXEL_COLORS[pixel_color],
                  (x_axis_base_position, y_axis_base_position, self.scaling_ratio, self.scaling_ratio))

    def get_screen_pixel(self, x_axis_position, y_axis_position):
        """
        This method tells whether the pixel on the x and y coordinates
        in the parameters is on or off.

        :param x_axis_position: the x coordinate to check
        :param y_axis_position: the y coordinate to check
        :return: the color value of the pixel (0 or 1)
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
        This method completely clears the screen.
        """
        self.screen_surface.fill(PIXEL_COLORS[0])

    @staticmethod
    def update_screen():
        """
        This method updates display by swapping the back and screen buffers 
        """
        display.flip()

    def set_screen_extended(self):
        """
        This method sets the screen to extended mode
        """
        display.quit()
        self.screen_height = SCREEN_HEIGHT[SCREEN_MODE_EXTENDED]
        self.screen_width = SCREEN_WIDTH[SCREEN_MODE_EXTENDED]
        self.init_display()

    def set_screen_normal(self):
        """
        This method sets the screen to normal mode
        """
        display.quit()
        self.screen_height = SCREEN_HEIGHT[SCREEN_MODE_NORMAL]
        self.screen_width = SCREEN_WIDTH[SCREEN_MODE_NORMAL]
        self.init_display()

    def scroll_screen_down(self, line_number_count):
        """
        This method scrolls the screen down by line_number_count lines

        :param line_number_count: the number of lines
        """
        for y_axis_position in xrange(self.screen_height - line_number_count, -1, -1):
            for x_axis_position in xrange(self.screen_width):
                pixel_color = self.get_screen_pixel(x_axis_position, y_axis_position)
                self.draw_screen_pixel(x_axis_position, y_axis_position + line_number_count, pixel_color)

        for y_axis_position in xrange(line_number_count):
            for x_axis_position in xrange(self.screen_width):
                self.draw_screen_pixel(x_axis_position, y_axis_position, 0)

        display.flip()

    def scroll_screen_left(self):
        """
        This method scrolls left the screen by 4 pixels
        """
        for y_axis_position in xrange(self.screen_height):
            for x_axis_position in xrange(4, self.screen_width):
                pixel_color = self.get_screen_pixel(x_axis_position, y_axis_position)
                self.draw_screen_pixel(x_axis_position - 4, y_axis_position, pixel_color)

        # Blank out the lines to the right of the ones we just scrolled
        for y_axis_position in xrange(self.screen_height):
            for x_axis_position in xrange(self.screen_width - 4, self.screen_width):
                self.draw_screen_pixel(x_axis_position, y_axis_position, 0)

        display.flip()

    def scroll_screen_right(self):
        """
        This method scrolls right the screen by 4 pixels
        """
        for y_axis_position in xrange(self.screen_height):
            for x_axis_position in xrange(self.screen_width - 4, -1, -1):
                pixel_color = self.get_screen_pixel(x_axis_position, y_axis_position)
                self.draw_screen_pixel(x_axis_position + 4, y_axis_position, pixel_color)

        # Blank out the lines to the left of the ones we just scrolled
        for y_axis_position in xrange(self.screen_height):
            for x_axis_position in xrange(4):
                self.draw_screen_pixel(x_axis_position, y_axis_position, 0)

        display.flip()
