#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from losoto.lib_operations import *

logging.debug('Loading CLIP module.')

def _run_parser(soltab, parser, step):
    axesToClip = parser.getarraystr( step, 'axesToClip' ) # no default
    clipLevel = parser.getfloat( step, 'clipLevel', 5. )
    log = parser.getbool( step, 'log', False )
    
    parser.checkSpelling( step, soltab, ['axesToClip', 'clipLevel', 'log'] )
    return run(soltab, axesToClip, clipLevel, log)

def run( soltab, axesToClip, clipLevel=5., log=False ):
    """
    Clip solutions around the median by a factor specified by the user.
    WEIGHT: flag compliant, putting weights into median is tricky

    Parameters
    ----------
    axesToClip : list of str
        axes along which to calculate the median (e.g. [time,freq])

    clipLevel : float, optional
        factor above/below median at which to clip, by default 5

    log : bool, optional
        clip is done in log10 space, by default False
    """

    import numpy as np

    def percentFlagged(w):
        return 100.*(weights.size-np.count_nonzero(weights))/float(weights.size)

    logging.info("Clipping soltab: "+soltab.name)

    # input check
    if len(axesToClip) < 1:
        logging.error("Please specify axes to clip.")
        return 1

    if clipLevel <= 0.:
        logging.error("Please specify a positive factor above/below median at which to clip.")
        return 1

    if soltab.getType() == 'amplitude' and not log:
        logging.warning('Amplitude solution tab detected and log=False. Amplitude solution tables should be treated in log space.')

    # some checks
    for i, axis in enumerate(axesToClip[:]):
        if axis not in soltab.getAxesNames():
            del axesToClip[i]
            logging.warning('Axis \"'+axis+'\" not found. Ignoring.')

    for vals, weights, coord, selection in soltab.getValuesIter(returnAxes=axesToClip, weight = True):

        initPercent = percentFlagged(weights)

        # first find the median and standard deviation
        if (weights == 0).all():
            valmedian = 0
        else:
            if log:
                valmedian = np.nanmedian(np.log10(vals[(weights != 0)]))
                rms = np.nanstd(np.log10(vals[(weights != 0)]))
                np.putmask(weights, np.abs(np.log10(vals)-valmedian) > rms * clipLevel, 0)
            else:
                valmedian = np.nanmedian(vals[(weights != 0)])
                rms = np.nanstd(vals[(weights != 0)])
                np.putmask(weights, np.abs(vals-valmedian) > rms * clipLevel, 0)
    
        # writing back the solutions
        soltab.setValues(weights, selection, weight=True)

        #print('max', np.max(vals[(weights != 0)]))
        #print('median', np.nanmedian(vals[(weights != 0)]))
        logging.debug('Percentage of data flagged (%s): %.3f%% -> %.3f%% (rms=%.2f)' \
            % (removeKeys(coord, axesToClip), initPercent, percentFlagged(weights), rms))

    soltab.addHistory('CLIP (over %s with %s sigma cut)' % (axesToClip, clipLevel))

    soltab.flush()
        
    return 0


