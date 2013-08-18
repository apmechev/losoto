#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Retrieving and writing data in H5parm format

import os, sys
import tables
import logging
import _version

# check for tables version
if int(tables.__version__.split('.')[0]) < 3:
    logging.critical('pyTables version must be >= 3.0.0, found: '+tables.__version__)
    sys.exit(1)

class h5parm():

    def __init__(self, h5parmFile, readonly = True, complevel = 9):
        """
        Keyword arguments:
        h5parmFile -- H5parm filename
        readonly -- if True the table is open in readonly mode (default=True)
        complevel -- compression level from 0 to 9 (default=9) when creating the file
        """
        if os.path.isfile(h5parmFile):
            if readonly:
                self.H = tables.openFile(h5parmFile, 'r')
            else:
                logging.warning('Appending to an existent file.')
                self.H = tables.openFile(h5parmFile, 'a')
        else:
            if readonly:
                raise Exception('Missing file '+h5parmFile+'.')
            else:
                # add a compression filter
                f = tables.Filters(complevel=complevel, complib='zlib')
                self.H = tables.openFile(h5parmFile, filters=f, mode='w')
        
        # if the file is new add the version of the h5parm
        # in losoto._version.__h5parmVersion__


    def __del__(self):
        """
        Flush and close the open table
        """
        self.H.close()


    def makeSolset(self, solsetName = ''):
        """
        Create a new solset, if the provided name is not given or exists
        then it falls back on the first available sol###
        """

        if solsetName in self.getSolsets().keys():
            logging.error('Solution set '+solsetName+' already present.')
            solsetName = ''


        if solsetName == '':
            solsetName = self._fisrtAvailSolsetName()
        
        logging.info('Creating new solution-set '+solsetName+'.')
        return self.H.create_group("/", solsetName)


    def getSolsets(self):
        """
        Return a dict with all the available solultion-sets (as a _ChildrenDict)
        """
        return self.H.root._v_children


    def _fisrtAvailSolsetName(self):
        """
        Create and return the first available solset name which
        has the form of "sol###"
        """
        nums = []
        for solset in self.getSolsets().keys():
            try:
                if solset[0:3] == 'sol':
                    nums.append(int(solset[3:6]))
            except:
                pass

        return "sol%03d" % min(list(set(range(1000)) - set(nums)))


    def makeSoltab(self, solset=None, soltype=None, descriptor={}):
        """
        Create a solution-table into a specified solution-set
        Keyword arguments:
        solset -- a solution-set name (String) or a Group instance
        soltype -- solution type (e.g. amplitude, phase)
        """
        if solset == None:
            raise Exception("Solution set not specified while adding a solution-table.")
        if soltype == None:
            raise Exception("Solution type not specified while adding a solution-table.")
        
        if type(solset) is str:
            solset = self.H.root._f_get_child(solset)

        soltabName = self._fisrtAvailSoltabName(solset, soltype)
        logging.info('Creating new solution-table '+soltabName+'.')

        return self.H.createTable(solset, soltabName, descriptor, soltype)


    def getSoltabs(self, solset=None):
        """
        Return a dict {name1: object1, name2: object2, ...}
        of all the available solultion-tables into a specified solution-set
        Keyword arguments:
        solset -- a solution-set name (String) or a Group instance
        Output: 
        A dict of all available solultion-tables 
        """
        if solset == None:
            raise Exception("Solution set not specified while querying for solution-tables list.")
        if type(solset) is str:
            solset = self.H.root._f_get_child(solset)

        soltabs = {}
        for soltabName, soltab in solset._v_children.iteritems():
            if not (soltabName == 'antenna' or soltabName == 'source'):
                soltabs[soltabName] = soltab

        return soltabs


    def getSoltab(self, solset=None, soltab=None):
        """
        Return a specific solution-table of a specific solution-set
        Keyword arguments:
        solset -- a solution-set name (String) or a Group instance
        soltab -- a solution-table name (String)
        """
        if solset == None:
            raise Exception("Solution-set not specified.")
        if soltab == None:
            raise Exception("Solution-table not specified.")

        if type(solset) is str:
            solset = self.H.root._f_get_child(solset)

        return solset._f_get_child(soltab)


    def _fisrtAvailSoltabName(self, solset=None, soltype=None):
        """
        Create and return the first available solset name which
        has the form of "sol###"
        Keyword arguments:
        solset -- a solution-set name as Group instance
        soltype -- type of solution (amplitude, phase, RM, clock...) as a string
        """
        if solset == None:
            raise Exception("Solution-set not specified while querying for solution-tables list.")
        if soltype == None:
            raise Exception("Solution type not specified while querying for solution-tables list.")

        nums = []
        for soltab in self.getSoltabs(solset):
            try:
                if soltab[-4:] == soltype:
                    nums.append(int(soltab[-4:]))
            except:
                pass

        return soltype+"%03d" % min(list(set(range(1000)) - set(nums)))


    def addRow(self, soltab=None, val=[]):
        """
        Add a single row to the given soltab
        Keyword arguments:
        soltab -- a solution-table instance
        val -- a list of all the field to insert, the order is important!
        """
        if soltab == None:
            raise Exception("Solution-table not specified while adding a new row.")

        soltab.append(val)


    def getAnt(self, solset):
        """
        Return a dict of all available antennas
        in the form {name1:[position coords],name2:[position coords],...}
        Keyword arguments:
        solset -- a solution-set name (String) or a Group instance
        """
        if solset == None:
            raise Exception("Solution-set not specified.")
        if type(solset) is str:
            solset = self.H.root._f_get_child(solset)

        ants = {}
        for x in solset.antenna:
            ants[x['name']] = x['position']
            
        return ants

    def getSou(self, solset):
        """
        Return a dict of all available sources
        in the form {name1:[ra,dec],name2:[ra,dec],...}
        Keyword arguments:
        solset -- a solution-set name (String) or a Group instance
        """
        if solset == None:
            raise Exception("Solution-set not specified.")
        if type(solset) is str:
            solset = self.H.root._f_get_child(solset)

        sources = {}
        for x in solset.source:
            sources[x['name']] = x['dir']
            
        return sources


class solHandler():
    """
    Generic class to pricipally handle selections
    """
    def __init__(self, table, selection = '', valAxes=['val','flag']):
        """
        Keyword arguments:
        tab -- table object
        selection -- a selection on the axis of the type "(ant == 'CS001LBA') & (pol == 'XX')"
        valAxes -- list of axis names which are not used to indexise the values
        """
        
        if not isinstance( table, tables.table.Table):
            logging.error("Object must be initialized with a tables.table.Table object.")
            return
        self.t = table
        self.selection = selection
        self.valAxes = valAxes
 

    def setSelection(self, selection = ''):
        """
        set a default selection criteria.
        Keyword arguments:
        selection -- a selection on the axis of the type "(ant == 'CS001LBA') & (pol == 'XX')"
        """
        self.selection = selection


    def makeSelection(self, append=False, **args):
        """
        Prepare a selection string based on the given arguments
        args are a list of valid axis of the form: {'pol':'XX','ant':['CS001HBA','CS002HBA']}
        """
        if append:
            s = self.selection + " & "
        else:
            s = ''
        for axis, val in args.items():

            if val == [] or val == '': continue

            # in case of a list of a single item, turn it into string
            if isinstance(val, list) and len(val) == 1: val = val[0]

            # iterate the list and add an entry for each element
            if isinstance(val, list):

                s += '( '
                for v in val:
                    s = s + "(" + axis + "=='" + v + "') | "
                # replace the last "|" with a "&"
                s = ') &'.join(s.rsplit('|', 1))

            elif isinstance(val, str):
                s = s + "(" + axis + "=='" + val + "') & "

            else:
                logging.error('Cannot handle type: '+str(type(val))+'when setting selections.')

        # remove the last "& "
        self.selection = s[:-2]


    def getType(self):
        """
        return the type of the solution-tables (it is stored in the title)
        """

        return self.t._v_title

    
    def getRowsIterator(self, selection = None):
        """
        Return a row iterator give a certain selection
        Keyword arguments:
        selection -- a selection on the axis of the type "(ant == 'CS001LBA') & (pol == 'XX')"
        """
        if selection == None: selection = self.selection

        if selection != '':
            return self.t.where(selection)
        else:
            return self.t.iterrows()


class solWriter(solHandler):

    def __init__(self, table, selection = '', valAxes=['val','flag']):
        solHandler.__init__(self, table = table, selection = selection, valAxes = valAxes)

    
    def setAxis(self, column = None, val = None, selection = None):
        """
        Set the value of a specific column
        """

        if selection == None: selection = self.selection

        for row in self.getRowsIterator(selection):
            row[column] = val
            row.update()


class solFetcher(solHandler):

    def __init__(self, table, selection = '', valAxes=['val','flag']):
        solHandler.__init__(self, table = table, selection = selection, valAxes = valAxes)


    def __getattr__(self, axis):
        """
        link any attribute with an "axis name" to getValuesAxis("axis name") or to
        getValuesGrid() if it is a valAxes
        """
        if axis in self.getAxes(valAxes = []):
            if axis in self.valAxes:
                return self.getValuesGrid(valAxis = axis, \
                        valAxes = [a for a in self.valAxes if a != axis])[0]
            else:
                return self.getValuesAxis(axis=axis)
        else:
            raise AttributeError("Axis \""+axis+"\" not found.")


    def getValuesAxis(self, axis='', selection=None):
        """
        Return a sorted list of all the possible values present along a specific axis (no duplicates)
        Keyword arguments:
        axis -- the axis name
        selection --
        """

        import numpy as np

        if selection == None: selection = self.selection

        if axis not in self.getAxes(valAxes = []):
            logging.error('Axis \"'+axis+'\" not found.')
            return []

        return list(np.unique( np.array( [ x[axis] for x in self.getRowsIterator(selection) ] ) ))


    def getValuesGrid(self, selection=None, valAxis = "val", valAxes = None, return_nrows = False):
        """
        Try to create a simple matrix of values. NaNs will be returned where the values are not available.
        Keyword arguments:
        selection -- a selection on the axis of the type "(ant == 'CS001LBA') & (pol == 'XX')"
        valAxis -- name of the value axis (use "flag" to obtain the matix of flags)
        notAxis -- list of axes names which are to ignore when looking for all the axes (use "val" when obtaining the matrix of flags) - WARNING: if igoring an axis which indexes multiple values, then a random value among those indexed by that axis is used!
        notAxis -- list of axes names which are to ignore when looking for all the axes (use "val" when obtaining the matrix of flags) - WARNING: if igoring an axis which index multiple values, then a random value among those possible indexed by that axis is used!
        return_nrows -- if True return a 3rd parameter that is the row numbers corresponding to every value in the same shape
        Return:
        ndarray of vals and a list with axis values in the form:
        [[axisvals1],[axisvals2],...]
        NOTE: each axis is sorted!
        """

        import numpy as np

        if valAxes == None: valAxes = self.valAxes
        if selection == None: selection = self.selection

        # retreive axes values in a list of numpy arrays
        axesVals = []
        axesIdx = []
        for axis in self.getAxes(valAxes = valAxes):
            axisVals, axisIdx = np.unique(np.array( [ x[axis] for x in self.getRowsIterator(selection) ] ), return_inverse=True)
            axesVals.append(axisVals)
            axesIdx.append(axisIdx)

        # create an ndarray and fill it with NaNs
        vals = np.ndarray(shape = [len(axis) for axis in axesVals])
        vals[:] = np.NAN
        if return_nrows: nrows = np.copy(vals)

        # refill the array with the correct values when they are available
        tempVals = []
        tempNrows = []
        for x in self.getRowsIterator(selection):
            tempVals.append(x[valAxis])
            tempNrows.append(x.nrow)
        vals[axesIdx] = np.array(tempVals)
        if return_nrows: nrows[axesIdx] = np.array(tempNrows)

        #vals[axesIdx] = np.array( [ x[valAxis] for x in self.getRowsIterator(selection) ] )

        if return_nrows:
            return vals, axesVals, nrows
        else:
            return vals, axesVals


    def getIterValuesGrid(self, selection=None, valAxis = "val", valAxes = None, returnAxes= [], return_nrows = False):
        """
        Return an iterator which yelds the values matrix (with axes = returnAxes) iterating along the other axes.
        E.g. if returnAxes are "freq" and "time", one gets a interetion over all the possible NxM
        matrix where N are the freq and M the time dimensions. The iterator returns also the 
        value of the iterAxes for an easy write back.
        Keyword arguments:
        iterAxes -- axes which are used to iterate the data
        Return:
        ndarray of dim=dim(returnAxes) and with the axes oriented as given
        it also returns the indexes of all the other axes (in correct order)
        corresponding to the returned array
        """
        
        import itertools
        import numpy as np

        if valAxes == None: valAxes = self.valAxes

        if return_nrows:
            vals, axesVals, nrows = self.getValuesGrid(selection=None, valAxis = valAxis, \
                    valAxes = valAxes, return_nrows = True)
        else:
            vals, axesVals = self.getValuesGrid(selection=None, valAxis = valAxis, valAxes = valAxes)

        axesName = self.getAxes(valAxes = valAxes)
        returnAxesIdx = [i for i, axis in enumerate(axesName) if axis in returnAxes]
        iterAxesIdx = [i for i, axis in enumerate(axesName) if axis not in returnAxes]

        # collect iterAxes dimensions
        iterAxesDim = []
        for axisIdx in iterAxesIdx:
            iterAxesDim.append(len(axesVals[axisIdx]))

        # move retrunAxes to the end of the vals array
        # preseving the respective order of returnAxesIdx and iterAxesIdx
        for i, axisIdx in enumerate(returnAxesIdx):
            vals = np.rollaxis(vals, axisIdx, vals.ndim)
            if return_nrows: nrows = np.rollaxis(nrows, axisIdx, nrows.ndim)
            for j, axisIdxCheck in enumerate(returnAxesIdx):
                if axisIdxCheck > axisIdx: returnAxesIdx[j] -= 1

        # generator to cycle over all the combinations of iterAxes
        # it "simply" get the vals of this particular combination of iterAxes
        # and return it together with the axesVals (for the iterAxes reduced the single value)
        def g():
            for axisIdx in np.ndindex(tuple(iterAxesDim)):
                thisAxesVals = axesVals[:]
                for j, i in enumerate(iterAxesIdx):
                    thisAxesVals[i] = axesVals[i][axisIdx[j]]
                if return_nrows: yield (vals[axisIdx], thisAxesVals, nrows[axisIdx])
                else: yield (vals[axisIdx], thisAxesVals)

        return g()


    def getAxes(self, valAxes = None):
        """
        Return a list with all the axis names in the correct order for
        slicing the getValuesGrid() reurned list.
        Keyword arguments:
        valAxes -- array of names of axes that are not to list
        """
        # remove the values columns from the axes
        if valAxes == None: valAxes = self.valAxes

        return [axis for axis in list(self.t.colpathnames) if axis not in valAxes]