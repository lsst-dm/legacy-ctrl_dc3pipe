#!/usr/bin/env python

import lsst.afw.image as afwImage

from lsst.pex.harness.Stage import Stage

class ValidateMetadataStage(Stage):

    """Validates that every field in metadataPolicy exists in the
    input metadata, before sending the event down the pipeline.  This
    will evolve as the pipeline evolves and the metadata requirements
    of each stage evolves.

    For the input of external (non-LSST) data these data's metadata
    should be generally be run through the TransformMetadata stage,
    with a survey-specific policy file specifying this mapping.
    """

    def process(self):
        self.activeClipboard = self.inputQueue.getNextDataset()
        metadataPolicy = self._policy.getPolicy("metadata")
        imageMetadataName = self._policy.get("imageMetadataName")
        metadata = self.activeClipboard.get(imageMetadataName)
        paramNames = metadataPolicy.paramNames(1)
        for paramName in paramNames:
            if not metadata.exists(paramName):
                raise RuntimeError, 'Unable to find \'%s\' in metadata' % (paramName))
            # TBD; VALIDATE AGAINST DICTIONARY FOR TYPE ETC
        self.outputQueue.addDataset(self.activeClipboard)
    

class TransformMetadataStage(Stage):

    """This stage takes an input set of metadata and transforms this
    to the LSST standard.  It will be input-dataset specific, and the
    mapping is described in the datatypePolicy.  The standard is to
    have a string in the datatypePolicy named metadataKeyword that
    represents the location of LSST metadata in the particular data
    set."""

    def process(self):
        self.activeClipboard = self.inputQueue.getNextDataset()
        metadataPolicy = self._policy.getPolicy("metadata")
        datatypePolicy = self._policy.getPolicy("datatype")
        imageMetadataName = self._policy.get("imageMetadataName")
        metadata = self.activeClipboard.get(imageMetadataName)

        if self._policy.exists("suffix"):
            suffix = self._policy.get("suffix")
        else:
            suffix = "Keyword"

        paramNames = metadataPolicy.paramNames(1)
        for paramName in paramNames:
            # If it already exists don't try and update it
            if metadata.exists(paramName):
                continue
        
            mappingKey = paramName + suffix
            if datatypePolicy.exists(mappingKey):
                keyword = datatypePolicy.getString(mappingKey)
                metadata.copy(paramName, metadata, keyword)
    
        # Any additional operations on the input data?
        if datatypePolicy.exists('convertDateobsToTai'):
            convertDateobsToTai = datatypePolicy.getBool('convertDateobsToTai')
            if convertDateobsToTai:
                dateobs  = metadata.getDouble('dateobs')
                dateTime = dafBase.DateTime(dateobs, dafBase.DateTime.UTC)
                dateobs  = dateTime.mjd(dafBase.DateTime.TAI)
                metadata.setDouble('dateobs', dateobs)

        if datatypePolicy.exists('convertDateobsToMidExposure'):
            convertDateobsToMidExposure = datatypePolicy.getBool('convertDateobsToMidExposure')
            if convertDateobsToMidExposure:
                dateobs  = metadata.getDouble('dateobs')
                dateobs += metadata.getDouble('exptime') * 0.5 / 3600. / 24.
                metadata.setDouble('dateobs', dateobs)

        self.activeClipboard.put(imageMetadataName, metadata)
        self.activeClipboard.put("wcsGuess", afwImage.Wcs(metadata))

        self.outputQueue.addDataset(self.activeClipboard)
