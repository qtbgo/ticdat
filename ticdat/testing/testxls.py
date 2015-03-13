import os
import unittest
import ticdat.utils as utils
from ticdat.ticdatfactory import TicDatFactory
from ticdat.testing.ticdattestutils import dietData, dietSchema, netflowData, netflowSchema, firesException
from ticdat.testing.ticdattestutils import sillyMeData, sillyMeSchema, makeCleanDir, failToDebugger, runSuite
import shutil

#uncomment decorator to drop into debugger for assertTrue, assertFalse failures
#@failToDebugger
class TestXls(unittest.TestCase):
    def firesException(self, f):
        e = firesException(f)
        if e :
            self.assertTrue("TicDatError" in e.__class__.__name__)
            return e.message
    def testDiet(self):
        tdf = TicDatFactory(**dietSchema())
        ticDat = tdf.FrozenTicDat(**{t:getattr(dietData(),t) for t in tdf.primary_key_fields})
        filePath = os.path.join(_scratchDir, "diet.xls")
        tdf.xls.write_file(ticDat, filePath)
        xlsTicDat = tdf.xls.create_tic_dat(filePath)
        self.assertTrue(tdf._sameData(ticDat, xlsTicDat))
        xlsTicDat.categories["calories"]["minNutrition"]=12
        self.assertFalse(tdf._sameData(ticDat, xlsTicDat))
    def testNetflow(self):
        tdf = TicDatFactory(**netflowSchema())
        ticDat = tdf.FrozenTicDat(**{t:getattr(netflowData(),t) for t in tdf.primary_key_fields})
        filePath = os.path.join(_scratchDir, "netflow.xls")
        tdf.xls.write_file(ticDat, filePath)
        xlsTicDat = tdf.xls.create_frozen_tic_dat(filePath)
        self.assertTrue(tdf._sameData(ticDat, xlsTicDat))
        def changeIt() :
            xlsTicDat.inflow['Pencils', 'Boston']["quantity"] = 12
        self.assertTrue(self.firesException(changeIt))
        self.assertTrue(tdf._sameData(ticDat, xlsTicDat))

        xlsTicDat = tdf.xls.create_tic_dat(filePath)
        self.assertTrue(tdf._sameData(ticDat, xlsTicDat))
        self.assertFalse(self.firesException(changeIt))
        self.assertFalse(tdf._sameData(ticDat, xlsTicDat))

        pkHacked = netflowSchema()
        pkHacked["primary_key_fields"]["nodes"] = "nimrod"
        tdfHacked = TicDatFactory(**pkHacked)
        self.assertTrue(self.firesException(lambda : tdfHacked.xls.write_file(ticDat, filePath)))
        tdfHacked.xls.write_file(ticDat, filePath, allow_overwrite =True)
        self.assertTrue("nodes : name" in self.firesException(lambda  :tdf.xls.create_tic_dat(filePath)))

    def testSilly(self):
        tdf = TicDatFactory(**sillyMeSchema())
        ticDat = tdf.TicDat(**sillyMeData())
        schema2 = sillyMeSchema()
        schema2["primary_key_fields"]["b"] = ("bField2", "bField1", "bField3")
        schema3 = sillyMeSchema()
        schema3["data_fields"]["a"] = ("aData2", "aData3", "aData1")
        schema4 = sillyMeSchema()
        schema4["data_fields"]["a"] = ("aData1", "aData3")
        schema5 = sillyMeSchema()
        _tuple = lambda x : tuple(x) if utils.containerish(x) else (x,)
        for t in ("a", "b") :
            schema5["data_fields"][t] = _tuple(schema5["data_fields"][t]) + _tuple(schema5["primary_key_fields"][t])
        schema5["primary_key_fields"] = {"a" : (), "b" : []}
        schema5["generator_tables"] = ["a", "c"]
        schema6 = sillyMeSchema()
        schema6["primary_key_fields"]["d"] = "dField"

        tdf2, tdf3, tdf4, tdf5, tdf6 = (TicDatFactory(**x) for x in (schema2, schema3, schema4, schema5, schema6))

        filePath = os.path.join(_scratchDir, "silly.xls")
        tdf.xls.write_file(ticDat, filePath)

        ticDat2 = tdf2.xls.create_tic_dat(filePath)
        self.assertFalse(tdf._sameData(ticDat, ticDat2))

        ticDat3 = tdf3.xls.create_tic_dat(filePath)
        self.assertTrue(tdf._sameData(ticDat, ticDat3))

        ticDat4 = tdf4.xls.create_tic_dat(filePath)
        for t in tdf.primary_key_fields:
            for k,v in getattr(ticDat4, t).items() :
                for _k, _v in v.items() :
                    self.assertTrue(getattr(ticDat, t)[k][_k] == _v)
                if set(v) == set(getattr(ticDat, t)[k]) :
                    self.assertTrue(t == "b")
                else :
                    self.assertTrue(t == "a")

        ticDat5 = tdf5.xls.create_tic_dat(filePath)
        self.assertTrue(tdf5._sameData(tdf._keyless(ticDat), ticDat5))
        self.assertTrue(callable(ticDat5.a) and callable(ticDat5.c) and not callable(ticDat5.b))

        ticDat6 = tdf6.xls.create_tic_dat(filePath)
        self.assertTrue(tdf._sameData(ticDat, ticDat6))
        self.assertTrue(firesException(lambda : tdf6._sameData(ticDat, ticDat6)))
        self.assertTrue(hasattr(ticDat6, "d") and utils.dictish(ticDat6.d))

        import xlwt
        book = xlwt.Workbook()
        for t in tdf.all_tables :
            sheet = book.add_sheet(t)
            for i,f in enumerate(tdf.primary_key_fields.get(t, ()) + tdf.data_fields.get(t, ())) :
                sheet.write(0, i, f)
            for rowInd, row in enumerate( [(1, 2, 3, 4), (1, 20, 30, 40), (10, 20, 30, 40)]) :
                for fieldInd, cellValue in enumerate(row):
                    sheet.write(rowInd+1, fieldInd, cellValue)
        if os.path.exists(filePath):
            os.remove(filePath)
        book.save(filePath)

        ticDatMan = tdf.xls.create_frozen_tic_dat(filePath)
        self.assertTrue(len(ticDatMan.a) == 2 and len(ticDatMan.b) == 3)
        self.assertTrue(ticDatMan.b[(1, 20, 30)]["bData"] == 40)

        ticDat.a["theboger"] = (1, None, 12)
        tdf.xls.write_file(ticDat, filePath, allow_overwrite=True)
        ticDatNone = tdf.xls.create_frozen_tic_dat(filePath)
        # THIS IS A FLAW - but a minor one. None's are hard to represent. It is turning into the empty string here.
        # not sure how to handle this, but documenting for now.
        self.assertFalse(tdf._sameData(ticDat, ticDatNone))
        self.assertTrue(ticDatNone.a["theboger"]["aData2"] == "")


_scratchDir = TestXls.__name__ + "_scratch"

def runTheTests(fastOnly=True) :
    makeCleanDir(_scratchDir)
    runSuite(TestXls, fastOnly=fastOnly)
    shutil.rmtree(_scratchDir)
# Run the tests.
if __name__ == "__main__":
    runTheTests()
