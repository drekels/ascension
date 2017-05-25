from ascension.settings import AscensionConf as conf


N_HEX_LINE = (0, 0)
S_HEX_LINE = (0, conf.tile_height)
NW_HEX_LINE = -conf.tile_point_slope, conf.horz_point_width - 1
SW_HEX_LINE = conf.tile_point_slope, conf.horz_point_width - 1
SE_HEX_LINE = (
    conf.tile_point_slope,
    conf.tile_height / 2 - 1 - conf.tile_point_slope*(conf.tile_width - 1)
)
NE_HEX_LINE = (
    -conf.tile_point_slope,
    conf.tile_height / 2 - 1 + conf.tile_point_slope*(conf.tile_width - 1)
)


def line_gtoe(line, x, y):
    a, b = line
    return y >= a*x + b


def line_gt(line, x, y):
    a, b = line
    return y > a*x + b


def line_ltoe(line, x, y):
    a, b = line
    return y <= a*x + b


def line_lt(line, x, y):
    a, b = line
    return y < a*x + b


def is_in_hex(x, y):
    return not (
           line_lt(N_HEX_LINE, x, y)
        or line_gtoe(S_HEX_LINE, x, y)
        or line_lt(NW_HEX_LINE, x, y)
        or line_gt(SW_HEX_LINE, x, y)
        or line_lt(SE_HEX_LINE, x, y)
        or line_gt(NE_HEX_LINE, x, y)
    )


def get_topleft_tile_point(i, j):
    x = i * (conf.tile_center_width + conf.horz_point_width - 1)
    y = j * conf.tile_height - (i % 2) * conf.tile_height / 2
    return x, y


def print_progress_bar (iteration, total, prefix = '', suffix = '', decimals = 1, length = 70, fill = u'\u2588'):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print u'\r{} |{}| {}% {}'.format(prefix, bar, percent, suffix),
    if iteration == total:
        print
    sys.stdout.flush()


