"""Read an explicit HP percentage only when no recognized non-HP trial exists."""
import re


def lowest_hp_match(results, scale=2):
    candidates=[]
    for box,text,score in results or []:
        if score < .95 or not re.search(r'\b(?:HP|health)\b',text,re.I):
            continue
        percentages=re.findall(r'\+?\s*(\d+(?:\.\d+)?)\s*%',text)
        if len(percentages)!=1:
            continue
        increase=float(percentages[0])
        if not 0<=increase<=300 or '-' in text:
            continue
        xs=[p[0]/scale for p in box];ys=[p[1]/scale for p in box]
        candidates.append((increase,min(xs),(min(xs),min(ys),max(xs)-min(xs),max(ys)-min(ys))))
    return min(candidates,key=lambda item:(item[0],item[1]))[2] if candidates else None


def read_lowest_hp(trials_image):
    import cv2
    from source.rabbit_hole_shop_vision import ShopVision
    results,_=ShopVision().engine(cv2.resize(trials_image,None,fx=2,fy=2))
    return lowest_hp_match(results)
