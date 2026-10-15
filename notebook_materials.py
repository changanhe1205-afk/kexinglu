"""Original, offline stationery artwork rendered at 2x with transparent edges."""
import base64
from functools import lru_cache
from io import BytesIO
import math
from PIL import Image, ImageDraw
from notebook_collage import element

PALETTES=[('#7C9279','#E6CDA4','#F6F1E5'),('#8AA6B4','#D9B7BB','#EFF3F5'),('#B48977','#D2B884','#F6EBDC')]
NAMES=['雏菊','银杏','橄榄枝','郁金香','山间日出','远山','信封','拍立得','相机','咖啡杯','旅行邮票','唱片','蝴蝶','月与星','行李箱','书签']

@lru_cache(maxsize=128)
def illustration(index,palette=0):
    img=Image.new('RGBA',(320,320));d=ImageDraw.Draw(img)
    a,b,p=PALETTES[palette];ink='#48544E'
    if index==0:
        for n in range(8):
            x=160+62*math.cos(n*math.pi/4);y=160+62*math.sin(n*math.pi/4)
            d.ellipse((x-35,y-35,x+35,y+35),fill=p,outline=a,width=3)
        d.ellipse((124,124,196,196),fill=b)
    elif index in (1,2,3):
        d.line((105,284,176,56),fill=ink,width=6)
        if index==1:
            d.pieslice((58,18,274,230),195,350,fill=b,outline=a,width=3)
            for x in range(90,250,25):d.line((166,196,x,95),fill=p,width=2)
        elif index==2:
            for n in range(5):
                y=90+n*34;x=164-n*10
                d.ellipse((x-72,y-24,x,y+14),fill=a)
                d.ellipse((x+4,y-48,x+64,y-8),fill=a)
        else:
            d.polygon([(110,72),(137,96),(164,44),(192,93),(223,64),(210,143),(175,171),(130,140)],fill=b)
            d.ellipse((83,179,143,220),fill=a);d.ellipse((144,205,229,239),fill=a)
    elif index in (4,5):
        d.ellipse((34,34,286,286),fill=p)
        d.ellipse((188,65,242,119),fill=b)
        d.polygon([(35,244),(103,113),(174,226),(223,159),(285,244)],fill=a)
        d.polygon([(58,265),(178,126),(275,265)],fill=ink)
        if index==4:d.arc((55,55,265,265),0,360,fill=b,width=4)
    elif index==6:
        d.rounded_rectangle((30,90,290,250),15,fill=p,outline=a,width=5)
        d.line([(32,95),(160,192),(288,95)],fill=a,width=4)
        d.ellipse((139,165,181,207),fill=b)
    elif index==7:
        d.rounded_rectangle((55,25,265,292),8,fill=p,outline=b,width=4)
        d.rectangle((72,44,248,227),fill=a);d.ellipse((185,65,216,96),fill=b)
        d.polygon([(72,227),(140,108),(248,227)],fill=ink)
    elif index==8:
        d.rounded_rectangle((25,87,295,247),24,fill=a)
        d.rounded_rectangle((80,55,145,103),8,fill=ink)
        d.ellipse((99,102,237,240),fill=p);d.ellipse((120,123,216,219),fill=ink)
        d.ellipse((142,137,167,162),fill=b);d.rectangle((257,107,279,126),fill=b)
    elif index==9:
        d.ellipse((60,235,264,270),fill=b)
        d.arc((199,124,288,217),265,100,fill=a,width=16)
        d.rounded_rectangle((70,120,229,248),35,fill=p,outline=a,width=5)
        for x in (112,151,190):d.arc((x-15,50,x+14,121),85,260,fill=b,width=5)
    elif index==10:
        d.rectangle((50,35,270,285),fill=p,outline=a,width=4)
        for x in range(50,275,22):
            d.ellipse((x-6,28,x+6,41),fill=(0,0,0,0));d.ellipse((x-6,278,x+6,291),fill=(0,0,0,0))
        d.rectangle((70,57,250,248),outline=b,width=5)
        d.ellipse((112,83,210,181),fill=b)
        d.polygon([(80,228),(143,130),(238,228)],fill=a)
    elif index==11:
        d.ellipse((35,35,285,285),fill=ink)
        for radius in (100,83,65):d.ellipse((160-radius,160-radius,160+radius,160+radius),outline=a,width=2)
        d.ellipse((122,122,198,198),fill=b);d.ellipse((153,153,167,167),fill=p)
    elif index==12:
        d.ellipse((31,60,154,205),fill=a);d.ellipse((167,60,290,205),fill=a)
        d.ellipse((65,174,155,270),fill=b);d.ellipse((166,174,256,270),fill=b)
        d.line((160,100,160,260),fill=ink,width=8)
        d.line([(160,111),(132,61),(114,52)],fill=ink,width=4)
        d.line([(160,111),(188,61),(207,52)],fill=ink,width=4)
    elif index==13:
        d.ellipse((40,35,261,268),fill=b);d.ellipse((104,9,294,211),fill=(0,0,0,0))
        for x,y in ((240,240),(244,88),(152,110)):
            d.polygon([(x,y-18),(x+6,y-6),(x+18,y),(x+6,y+6),(x,y+18),(x-6,y+6),(x-18,y),(x-6,y-6)],fill=a)
    elif index==14:
        d.rounded_rectangle((119,35,203,90),10,outline=ink,width=10)
        d.rounded_rectangle((54,81,269,269),22,fill=b,outline=ink,width=5)
        for x in (93,221):d.line((x,90,x,263),fill=a,width=12)
        d.rounded_rectangle((121,143,192,195),7,fill=p)
    else:
        d.polygon([(87,23),(238,23),(238,287),(162,240),(87,287)],fill=a)
        d.ellipse((129,83,195,149),fill=b);d.line((162,146,162,202),fill=p,width=4)
    img=img.resize((160,160),Image.Resampling.LANCZOS);buf=BytesIO();img.save(buf,'PNG')
    return base64.b64encode(buf.getvalue()).decode('ascii')

EXTRA_NAMES={
    'travel':['登机牌','旅行车票','目的地路标','指南针','露营帐篷','热气球','海边灯塔','帆船','城市天际线','旅行地图','徒步靴','行程挂牌'],
    'daily':['橘猫','小狗','草莓','樱桃','牛角包','抹茶蛋糕','冰饮','雨伞','晴天白云','彩虹','耳机','打开的书'],
    'frame':['拍立得空框','胶片空框','邮票空框','撕纸边框','花边圆框','双线标签','波点相框','四角贴纸框'],
}

@lru_cache(maxsize=32)
def extra_art(category,i):
    """Distinct transparent silhouettes, including empty frames for layering photos."""
    img=Image.new('RGBA',(320,320));d=ImageDraw.Draw(img)
    ink='#465750';cream='#FCF3DF';green='#88A68B';gold='#E2B568';pink='#DCA0A0';blue='#8DAFBF'
    if category=='travel':
        if i in (0,1):
            d.rounded_rectangle((18,68,302,252),16,fill=cream,outline=blue if i==0 else green,width=4)
            for y in range(77,250,15):d.line((230,y,230,y+7),fill=ink,width=2)
            d.rectangle((20,70,228,104),fill=blue if i==0 else green)
            d.text((37,82),'BOARDING PASS' if i==0 else 'RAIL JOURNEY',fill=ink,font_size=15)
            d.text((38,132),'FROM  >  TO',fill=ink,font_size=20)
            for n in range(28):
                x=37+n*5;d.line((x,194,x,226),fill=ink,width=2 if n%3 else 4)
            d.text((248,143),'01',fill=ink,font_size=23)
        elif i==2:
            d.line((158,38,158,293),fill=ink,width=12)
            d.polygon([(39,60),(232,60),(281,98),(232,136),(39,136)],fill=green)
            d.polygon([(278,163),(90,163),(40,196),(90,233),(278,233)],fill=gold)
            d.text((70,88),'GO EXPLORE',fill=cream,font_size=18)
        elif i==3:
            d.ellipse((39,39,281,281),fill=cream,outline=gold,width=10)
            d.ellipse((61,61,259,259),outline=ink,width=2)
            d.polygon([(160,71),(190,177),(160,160),(129,177)],fill=pink)
            d.polygon([(160,249),(129,143),(160,160),(190,143)],fill=blue)
            d.text((153,42),'N',fill=ink,font_size=18)
        elif i==4:
            d.ellipse((18,254,302,289),fill=green)
            d.polygon([(38,268),(156,65),(285,268)],fill=gold)
            d.polygon([(107,269),(156,127),(220,269)],fill=ink)
            d.line((146,60,285,270),fill=cream,width=5)
        elif i==5:
            d.ellipse((65,24,255,219),fill=pink)
            d.ellipse((111,24,209,219),fill=gold)
            d.line((111,193,137,252),fill=ink,width=3);d.line((209,193,185,252),fill=ink,width=3)
            d.rounded_rectangle((127,246,195,293),7,fill=green)
        elif i==6:
            d.polygon([(105,270),(122,92),(203,92),(224,270)],fill=cream,outline=ink,width=3)
            for y in (125,196):d.polygon([(116,y),(209,y),(215,y+32),(113,y+32)],fill=pink)
            d.rectangle((115,67,210,104),fill=gold);d.polygon([(108,65),(160,30),(218,65)],fill=ink)
            d.arc((23,240,297,311),182,357,fill=blue,width=10)
        elif i==7:
            d.line((167,30,167,251),fill=ink,width=5)
            d.polygon([(156,42),(156,220),(37,220)],fill=cream,outline=blue,width=3)
            d.polygon([(179,76),(272,220),(179,220)],fill=pink)
            d.polygon([(32,237),(290,237),(250,277),(77,277)],fill=ink)
            d.arc((20,261,295,303),0,180,fill=blue,width=6)
        elif i==8:
            for x,y,w,c in [(28,122,52,blue),(87,69,63,green),(164,104,47,pink),(226,45,62,gold)]:
                d.rectangle((x,y,x+w,277),fill=c)
                for yy in range(y+16,260,30):
                    for xx in range(x+10,x+w-8,20):d.rectangle((xx,yy,xx+7,yy+12),fill=cream)
            d.line((15,280,306,280),fill=ink,width=5)
        elif i==9:
            d.polygon([(20,72),(111,44),(209,76),(299,47),(299,253),(209,279),(111,247),(20,278)],fill=cream,outline=green,width=4)
            d.line([(30,210),(103,126),(195,210),(283,117)],fill=blue,width=13)
            for x in (111,209):d.line((x,80,x,247),fill=gold,width=3)
            d.ellipse((170,75,231,136),fill=pink);d.polygon([(176,122),(202,164),(226,122)],fill=pink)
            d.ellipse((190,91,213,113),fill=cream)
        elif i==10:
            d.polygon([(78,41),(177,41),(181,174),(269,211),(278,257),(48,257),(48,165)],fill=gold,outline=ink,width=4)
            d.rounded_rectangle((40,250,286,277),8,fill=ink)
            for y in range(78,182,25):d.line((126,y,178,y),fill=cream,width=6)
        else:
            d.arc((104,16,218,104),180,360,fill=ink,width=8)
            d.polygon([(70,66),(249,66),(276,99),(276,282),(43,282),(43,99)],fill=green)
            d.ellipse((151,81,169,99),fill=cream)
            d.text((74,137),'ADVENTURE',fill=cream,font_size=24)
            d.text((78,192),'KEEP GOING',fill=cream,font_size=19)
    elif category=='daily':
        if i in (0,1):
            c=gold if i==0 else '#B68C72'
            d.ellipse((67,91,253,279),fill=c)
            if i==0:
                d.polygon([(70,144),(70,45),(136,110)],fill=c);d.polygon([(184,110),(250,45),(250,144)],fill=c)
                d.polygon([(85,118),(83,73),(115,109)],fill=pink);d.polygon([(205,109),(238,73),(236,118)],fill=pink)
            else:
                d.ellipse((25,86,100,242),fill=ink);d.ellipse((220,86,295,242),fill=ink)
            for x in (116,206):d.ellipse((x-6,166,x+6,179),fill=ink)
            d.polygon([(151,195),(169,195),(160,207)],fill=ink)
            d.arc((137,192,183,230),0,180,fill=ink,width=3)
        elif i==2:
            d.polygon([(58,105),(261,105),(280,169),(159,287),(40,169)],fill=pink)
            d.polygon([(76,111),(105,75),(146,88),(162,42),(184,86),(234,70),(251,115)],fill=green)
            for x,y in [(88,153),(151,137),(218,154),(121,202),(181,206),(159,251)]:d.ellipse((x,y,x+6,y+12),fill=cream)
        elif i==3:
            d.line([(89,191),(165,43),(232,189)],fill=green,width=8)
            d.ellipse((45,167,145,272),fill=pink);d.ellipse((180,166,281,271),fill='#BE7979')
            d.ellipse((158,33,241,67),fill=green)
        elif i==4:
            d.ellipse((31,81,289,248),fill=gold);d.ellipse((88,149,235,270),fill=(0,0,0,0))
            for x in (96,146,196):d.line((x,93,x+20,164),fill=cream,width=7)
        elif i==5:
            d.polygon([(51,124),(271,124),(271,264),(51,264)],fill=cream)
            d.rectangle((51,151,271,177),fill=green);d.rectangle((51,222,271,247),fill=green)
            d.polygon([(51,124),(197,62),(271,124)],fill=green)
            d.ellipse((166,69,201,104),fill=pink)
        elif i==6:
            d.polygon([(65,94),(252,94),(225,290),(92,290)],fill=blue,outline=ink,width=3)
            d.line([(175,250),(198,48),(247,25)],fill=pink,width=12)
            for x,y in [(111,127),(162,148),(183,204)]:d.rounded_rectangle((x,y,x+30,y+30),5,fill=cream)
            d.ellipse((65,86,252,114),outline=ink,width=4)
        elif i==7:
            d.line((160,80,160,260),fill=ink,width=6);d.arc((109,232,163,287),0,180,fill=ink,width=6)
            d.pieslice((32,38,288,285),180,360,fill=blue)
            d.pieslice((99,38,221,285),180,360,fill=pink)
        elif i==8:
            d.ellipse((47,35,196,184),fill=gold)
            for x,y,r in [(101,178,59),(161,151,65),(221,180,55)]:d.ellipse((x-r,y-r,x+r,y+r),fill=cream)
            d.rounded_rectangle((47,180,276,242),28,fill=cream)
        elif i==9:
            for radius,c in [(130,pink),(103,gold),(76,green),(49,blue)]:d.arc((160-radius,180-radius,160+radius,180+radius),180,360,fill=c,width=22)
            for x in (35,251):d.ellipse((x-14,160,x+49,216),fill=cream)
        elif i==10:
            d.arc((45,31,275,281),180,360,fill=ink,width=22)
            d.rounded_rectangle((34,149,96,268),18,fill=blue);d.rounded_rectangle((224,149,286,268),18,fill=pink)
        else:
            d.polygon([(25,72),(113,56),(160,84),(207,56),(295,72),(295,267),(205,251),(160,279),(114,251),(25,267)],fill=cream,outline=green,width=5)
            d.line((160,85,160,272),fill=gold,width=4)
            for y in range(112,234,28):
                d.line((45,y,131,y-8),fill=gold,width=3);d.line((185,y-8,275,y),fill=gold,width=3)
    else:
        if i==0:
            d.rectangle((25,21,295,301),fill=cream);d.rectangle((43,40,277,251),fill=(0,0,0,0))
        elif i==1:
            d.rectangle((18,21,302,298),fill=ink);d.rectangle((52,42,268,277),fill=(0,0,0,0))
            for y in range(36,289,29):
                for x in (27,280):d.rounded_rectangle((x,y,x+12,y+16),3,fill=cream)
        elif i==2:
            d.rectangle((25,25,295,295),fill=cream);d.rectangle((46,46,274,274),fill=(0,0,0,0))
            for n in range(32,296,22):
                for box in [(n-6,19,n+6,31),(n-6,289,n+6,301),(19,n-6,31,n+6),(289,n-6,301,n+6)]:d.ellipse(box,fill=(0,0,0,0))
        elif i==3:
            d.polygon([(20,29),(75,20),(125,33),(171,21),(220,32),(291,18),(298,287),(240,298),(189,286),(143,301),(90,289),(22,301)],fill='#E7D6B7')
            d.rectangle((41,48,275,271),fill=(0,0,0,0))
        elif i==4:
            d.ellipse((31,31,289,289),outline=green,width=7)
            for n in range(16):
                x=160+129*math.cos(n*math.pi/8);y=160+129*math.sin(n*math.pi/8)
                d.ellipse((x-10,y-10,x+10,y+10),fill=pink if n%2 else gold)
        elif i==5:
            for inset in (25,38):d.rounded_rectangle((inset,74+inset/3,320-inset,245-inset/3),18,outline=green,width=3)
        elif i==6:
            d.rectangle((25,25,295,295),outline=pink,width=19)
            for n in range(35,291,24):
                for x,y in [(n,33),(n,287),(33,n),(287,n)]:d.ellipse((x-3,y-3,x+3,y+3),fill=cream)
        else:
            d.rectangle((34,34,286,286),outline=green,width=3)
            for x,y in [(26,26),(252,26),(26,252),(252,252)]:d.rectangle((x,y,x+42,y+42),fill=gold)
    img=img.resize((240,240),Image.Resampling.LANCZOS);buf=BytesIO();img.save(buf,'PNG')
    return base64.b64encode(buf.getvalue()).decode('ascii')


@lru_cache(maxsize=8)
def catalog(category):
    # Treat these as templates: the studio deep-copies on insertion.
    if category in EXTRA_NAMES:
        return [(name,element('image',image=extra_art(category,i),mime='image/png',name=name,text='',
                 w=240 if category=='frame' else 125,h=240 if category=='frame' else 125))
                for i,name in enumerate(EXTRA_NAMES[category])]
    if category=='sticker':
        return [(f'{name} · {tone}',element('image',image=illustration(i,k),mime='image/png',name=name,text='',w=110,h=110))
                for k,tone in enumerate(('山野','雾蓝','复古')) for i,name in enumerate(NAMES)]
    if category=='tape':
        colors=['#92B7C8','#E4BCC3','#A7B89A','#DBC596','#B6A4C4','#C1C5CD']
        return [(f'{label}胶带 {i+1}',element('tape',text='·  ·  ·  ·  ·  ·  ·' if patterned else '',
                color='#FFFDF0',size=17,background=c,w=170,h=32,rotation=-4))
                for patterned,label in [(False,'素色'),(True,'点点')] for i,c in enumerate(colors)]
    if category=='note':
        labels=['今日清单','旅行摘录','一日三餐','观影随记','天气晴','给未来的信','沿途所见','小小确幸']
        return [(name,element(text=name+'\n\n写下你想留下的内容',background=PALETTES[i%3][2],
                             font='KaiTi' if i%2 else 'Microsoft YaHei',size=17,w=210,h=180,rotation=-2 if i%2 else 2)) for i,name in enumerate(labels)]
    return []
