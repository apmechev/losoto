#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from losoto.lib_operations import *
import scipy.ndimage as nd

logging.debug('Loading INTERPOLATE module.')

def _run_parser(soltab, parser, step):
    outSoltab = parser.getstr( step, 'outSoltab') # no default
    axisToRegrid = parser.getstr( step, 'axisToRegrid') # no default
    newDelta = parser.getstr( step, 'newDelta') # no default
    delta = parser.getstr( step, 'delta', '')
    maxFlaggedWidth = parser.getint( step, 'maxFlaggedWidth', 0)

    parser.checkSpelling( step, soltab, ['outSoltab', 'axisToRegrid', 'newDelta', 'delta', 'maxFlaggedWidth'])
    return run( soltab, outSoltab, axisToRegrid, newDelta, delta, maxFlaggedWidth)


def _regrid_axis(vals, delta, newdelta):
    """
    Regrids an axis

    Parameters
    ----------
    vals : array
        Array of axis values to regrid

    delta : float
        Fundamental sampling width of input values

    newdelta : float
        Desired sampling width of regridded values

    Returns
    -------
    vals_new : array
        Array of new values
    """
    offset = newdelta / 2.0 - 0.5 * delta
    freqmin = np.min(vals) + offset
    freqmax = np.max(vals) + offset
    vals_new  = np.arange(freqmin, freqmax + newdelta / 2.0, newdelta)

    return vals_new


def _convert_strval(val):
    """
    Converts a string value with units to a float

    Parameters
    ----------
    val : str or float
        Value to convert. Units can be seconds ("s") or "Hz". E.g., "100kHz" or "10s"

    Returns
    -------
    val : float
        Value in fundamental units (s or Hz)
    """
    if type(val) is str or type(val) is unicode:
        letters = [1 for s in val[::-1] if s.isalpha()]
        indx = len(val) - sum(letters)
        unit = val[indx:]
        if unit.strip().lower() == 'hz' or unit.strip().lower() == 's':
            conversion = 1.0
        elif unit.strip().lower() == 'khz' or unit.strip().lower() == 'ks':
            conversion = 1e3
        elif unit.strip().lower() == 'mhz' or unit.strip().lower() == 'ms':
            conversion = 1e6
        else:
            logging.error("The unit on delta was not understood.")
            return 1
        val = float(val[:indx]) * conversion
    else:
        val = val

    return val


def run( soltab, outsoltab, axisToRegrid, newdelta, delta='', maxFlaggedWidth=0):
    """
    This operation for LoSoTo implements regridding and linear interpolation of data for an axis.
    WEIGHT: compliant

    Parameters
    ----------
    outsoltab: str
        Name of output soltab

    axisToRegrid : str
        Name of the axis for which regridding/interpolation will be done

    newdelta : float or str
        Fundamental width between samples after regridding. E.g., "100kHz" or "10s"

    delta : float or str, optional
        Fundamental width between samples in axisToRegrid. E.g., "100kHz" or "10s". If "",
        it is calculated from the axisToRegrid values

    maxFlaggedWidth : int, optional
        Maximum allowable width in number of samples (after regridding) above which
        interpolated values are flagged (e.g., maxFlaggedWidth = 5 would allow gaps of
        5 samples or less to be interpolated across but gaps of 6 or more would be
        flagged)
    """
    # Check inputs
    if axisToRegrid not in soltab.getAxesNames():
        logging.error('Axis \"'+axisToRegrid+'\" not found.')
        return 1
    if axisToRegrid not in ['freq', 'time']:
        logging.error('Axis \"'+axisToRegrid+'\" must be either time or freq.')
        return 1
    newdelta = _convert_strval(newdelta)
    if delta == "":
        deltas = soltab.getAxisValues(axisToRegrid)[1:] - soltab.getAxisValues(axisToRegrid)[:-1]
        delta = np.min(deltas)
        logging.info('Using {} for delta'.format(delta))
    else:
        delta = _convert_strval(delta)

    # Regrid axis
    axisind = soltab.getAxesNames().index(axisToRegrid)
    orig_axisvals = soltab.getAxisValues(axisToRegrid)
    new_axisvals = _regrid_axis(orig_axisvals, delta, newdelta)
    orig_shape = soltab.val.shape
    new_shape = list(orig_shape)
    new_shape[axisind] = len(new_axisvals)
    new_vals = np.zeros(new_shape, dtype='float')
    new_weights = np.zeros(new_shape, dtype='float')

    for vals, weights, coord, selection in soltab.getValuesIter(returnAxes=[axisToRegrid], weight=True):
        mask = np.not_equal(weights, 0.0)
        if np.sum(mask) > 2:
            # If there are at least two unflagged points, interpolate with mask
            new_vals[selection] = np.interp(new_axisvals, orig_axisvals[mask], vals[mask])

            # For the weights, interpolate without the mask
            new_weights[selection] = np.round(np.interp(new_axisvals, orig_axisvals, weights))

        # Check for flagged gaps
        if maxFlaggedWidth > 1:
            inv_weights = new_weights[selection].astype(bool).squeeze()
            rank = len(inv_weights.shape)
            connectivity = nd.generate_binary_structure(rank, rank)
            mask_labels, count = nd.label(~inv_weights, connectivity)
            for i in range(count):
                ind = np.where(mask_labels == i+1)
                gapsize = len(ind[0])
                if gapsize <= maxFlaggedWidth:
                    # Unflag narrow gaps
                    selection[axisind] = ind[0]
                    new_weights[selection] = 1.0

    # Write new soltab
    solset = soltab.getSolset()
    axesVals = []
    for axisName in soltab.getAxesNames():
        if axisName == axisToRegrid:
            axesVals.append(new_axisvals)
        else:
            axesVals.append(soltab.getAxisValues(axisName))
    s = solset.makeSoltab(soltab.getType(), outsoltab,
        axesNames=soltab.getAxesNames(), axesVals=axesVals, vals=new_vals, weights=new_weights)
    s.addHistory('CREATE by INTERPOLATE operation from '+soltab.name+'.')

    return 0
