from porescene.color import Color


def test_rgb():
    c1 = Color("85A2E6")
    assert c1.hex == "85A2E6"
    assert c1.hexa == "85A2E6FF"
    assert c1.rgb == (133, 162, 230)
    assert c1.nrgb == (133 / 255, 162 / 255, 230 / 255)
    assert c1.lnrgb == (0.23455058216100522, 0.3613067797835095, 0.7912979403326302)


def test_classmethods():
    c = Color.from_nrgb(0.6901960784313725, 0.07450980392156863, 0.10588235294117647)
    assert c.hex == "B0131B"
    assert c.rgb == (176, 19, 27)
