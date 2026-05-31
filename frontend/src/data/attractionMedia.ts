export type AttractionMedia = {
  attractionId: string;
  name: string;
  cover: string | null;
  samples: string[];
  alt: string;
  imageCount: number;
};

export const attractionMediaById: Record<string, AttractionMedia> = {
  "lingshan-ls-001": {
    attractionId: "lingshan-ls-001",
    name: "灵山大照壁",
    cover: "/assets/attractions/lingshan-ls-001/cover.jpg",
    samples: ["/assets/attractions/lingshan-ls-001/cover.jpg", "/assets/attractions/lingshan-ls-001/sample-1.jpg", "/assets/attractions/lingshan-ls-001/sample-2.jpg"],
    alt: "灵山大照壁景点封面",
    imageCount: 3,
  },
  "lingshan-ls-002": {
    attractionId: "lingshan-ls-002",
    name: "五明桥",
    cover: "/assets/attractions/lingshan-ls-002/cover.jpg",
    samples: ["/assets/attractions/lingshan-ls-002/cover.jpg"],
    alt: "五明桥景点封面",
    imageCount: 1,
  },
  "lingshan-ls-003": {
    attractionId: "lingshan-ls-003",
    name: "佛足坛",
    cover: "/assets/attractions/lingshan-ls-003/cover.jpg",
    samples: ["/assets/attractions/lingshan-ls-003/cover.jpg", "/assets/attractions/lingshan-ls-003/sample-1.jpg"],
    alt: "佛足坛景点封面",
    imageCount: 2,
  },
  "lingshan-ls-004": {
    attractionId: "lingshan-ls-004",
    name: "五智门",
    cover: "/assets/attractions/lingshan-ls-004/cover.jpg",
    samples: ["/assets/attractions/lingshan-ls-004/cover.jpg", "/assets/attractions/lingshan-ls-004/sample-1.jpg"],
    alt: "五智门景点封面",
    imageCount: 2,
  },
  "lingshan-ls-005": {
    attractionId: "lingshan-ls-005",
    name: "菩提大道",
    cover: "/assets/attractions/lingshan-ls-005/cover.jpg",
    samples: ["/assets/attractions/lingshan-ls-005/cover.jpg", "/assets/attractions/lingshan-ls-005/sample-1.jpg", "/assets/attractions/lingshan-ls-005/sample-2.jpg"],
    alt: "菩提大道景点封面",
    imageCount: 3,
  },
  "lingshan-ls-006": {
    attractionId: "lingshan-ls-006",
    name: "九龙灌浴",
    cover: "/assets/attractions/lingshan-ls-006/cover.jpg",
    samples: ["/assets/attractions/lingshan-ls-006/cover.jpg", "/assets/attractions/lingshan-ls-006/sample-1.jpg", "/assets/attractions/lingshan-ls-006/sample-2.jpg"],
    alt: "九龙灌浴景点封面",
    imageCount: 3,
  },
  "lingshan-ls-007": {
    attractionId: "lingshan-ls-007",
    name: "降魔浮雕",
    cover: "/assets/attractions/lingshan-ls-007/cover.jpg",
    samples: ["/assets/attractions/lingshan-ls-007/cover.jpg", "/assets/attractions/lingshan-ls-007/sample-1.jpg", "/assets/attractions/lingshan-ls-007/sample-2.jpg", "/assets/attractions/lingshan-ls-007/sample-3.jpg"],
    alt: "降魔浮雕景点封面",
    imageCount: 4,
  },
  "lingshan-ls-008": {
    attractionId: "lingshan-ls-008",
    name: "阿育王柱",
    cover: "/assets/attractions/lingshan-ls-008/cover.jpg",
    samples: ["/assets/attractions/lingshan-ls-008/cover.jpg", "/assets/attractions/lingshan-ls-008/sample-1.jpg"],
    alt: "阿育王柱景点封面",
    imageCount: 2,
  },
  "lingshan-ls-009": {
    attractionId: "lingshan-ls-009",
    name: "百子戏弥勒",
    cover: "/assets/attractions/lingshan-ls-009/cover.jpg",
    samples: ["/assets/attractions/lingshan-ls-009/cover.jpg", "/assets/attractions/lingshan-ls-009/sample-1.jpg"],
    alt: "百子戏弥勒景点封面",
    imageCount: 2,
  },
  "lingshan-ls-010": {
    attractionId: "lingshan-ls-010",
    name: "祥符禅寺",
    cover: "/assets/attractions/lingshan-ls-010/cover.jpg",
    samples: ["/assets/attractions/lingshan-ls-010/cover.jpg", "/assets/attractions/lingshan-ls-010/sample-1.jpg", "/assets/attractions/lingshan-ls-010/sample-2.jpg"],
    alt: "祥符禅寺景点封面",
    imageCount: 3,
  },
  "lingshan-ls-011": {
    attractionId: "lingshan-ls-011",
    name: "灵山大佛",
    cover: "/assets/attractions/lingshan-ls-011/cover.jpg",
    samples: ["/assets/attractions/lingshan-ls-011/cover.jpg", "/assets/attractions/lingshan-ls-011/sample-1.jpg", "/assets/attractions/lingshan-ls-011/sample-2.jpg", "/assets/attractions/lingshan-ls-011/sample-3.jpg"],
    alt: "灵山大佛景点封面",
    imageCount: 4,
  },
  "lingshan-ls-012": {
    attractionId: "lingshan-ls-012",
    name: "佛教文化博览馆",
    cover: "/assets/attractions/lingshan-ls-012/cover.jpg",
    samples: ["/assets/attractions/lingshan-ls-012/cover.jpg", "/assets/attractions/lingshan-ls-012/sample-1.jpg", "/assets/attractions/lingshan-ls-012/sample-2.jpg"],
    alt: "佛教文化博览馆景点封面",
    imageCount: 3,
  },
  "lingshan-ls-013": {
    attractionId: "lingshan-ls-013",
    name: "灵山梵宫",
    cover: "/assets/attractions/lingshan-ls-013/cover.jpg",
    samples: ["/assets/attractions/lingshan-ls-013/cover.jpg", "/assets/attractions/lingshan-ls-013/sample-1.jpg", "/assets/attractions/lingshan-ls-013/sample-2.jpg", "/assets/attractions/lingshan-ls-013/sample-3.jpg", "/assets/attractions/lingshan-ls-013/sample-4.jpg"],
    alt: "灵山梵宫景点封面",
    imageCount: 5,
  },
  "lingshan-ls-014": {
    attractionId: "lingshan-ls-014",
    name: "五印坛城",
    cover: "/assets/attractions/lingshan-ls-014/cover.jpg",
    samples: ["/assets/attractions/lingshan-ls-014/cover.jpg", "/assets/attractions/lingshan-ls-014/sample-1.jpg", "/assets/attractions/lingshan-ls-014/sample-2.jpg", "/assets/attractions/lingshan-ls-014/sample-3.jpg", "/assets/attractions/lingshan-ls-014/sample-4.jpg"],
    alt: "五印坛城景点封面",
    imageCount: 5,
  },
  "lingshan-ls-015": {
    attractionId: "lingshan-ls-015",
    name: "曼飞龙塔",
    cover: "/assets/attractions/lingshan-ls-015/cover.jpg",
    samples: ["/assets/attractions/lingshan-ls-015/cover.jpg", "/assets/attractions/lingshan-ls-015/sample-1.jpg", "/assets/attractions/lingshan-ls-015/sample-2.jpg"],
    alt: "曼飞龙塔景点封面",
    imageCount: 3,
  },
  "lingshan-ls-016": {
    attractionId: "lingshan-ls-016",
    name: "无尽意斋",
    cover: "/assets/attractions/lingshan-ls-016/cover.jpg",
    samples: ["/assets/attractions/lingshan-ls-016/cover.jpg"],
    alt: "无尽意斋景点封面",
    imageCount: 1,
  },
  "nianhuawan-nh-001": {
    attractionId: "nianhuawan-nh-001",
    name: "拈花广场",
    cover: "/assets/attractions/nianhuawan-nh-001/cover.jpg",
    samples: ["/assets/attractions/nianhuawan-nh-001/cover.jpg", "/assets/attractions/nianhuawan-nh-001/sample-1.jpg"],
    alt: "拈花广场景点封面",
    imageCount: 2,
  },
  "nianhuawan-nh-002": {
    attractionId: "nianhuawan-nh-002",
    name: "梵天花海",
    cover: "/assets/attractions/nianhuawan-nh-002/cover.jpg",
    samples: ["/assets/attractions/nianhuawan-nh-002/cover.jpg", "/assets/attractions/nianhuawan-nh-002/sample-1.jpg", "/assets/attractions/nianhuawan-nh-002/sample-2.jpg", "/assets/attractions/nianhuawan-nh-002/sample-3.jpg"],
    alt: "梵天花海景点封面",
    imageCount: 4,
  },
  "nianhuawan-nh-003": {
    attractionId: "nianhuawan-nh-003",
    name: "香月花街",
    cover: "/assets/attractions/nianhuawan-nh-003/cover.jpg",
    samples: ["/assets/attractions/nianhuawan-nh-003/cover.jpg", "/assets/attractions/nianhuawan-nh-003/sample-1.jpg", "/assets/attractions/nianhuawan-nh-003/sample-2.jpg", "/assets/attractions/nianhuawan-nh-003/sample-3.jpg", "/assets/attractions/nianhuawan-nh-003/sample-4.jpg"],
    alt: "香月花街景点封面",
    imageCount: 5,
  },
  "nianhuawan-nh-004": {
    attractionId: "nianhuawan-nh-004",
    name: "拈花堂",
    cover: "/assets/attractions/nianhuawan-nh-004/cover.jpg",
    samples: ["/assets/attractions/nianhuawan-nh-004/cover.jpg"],
    alt: "拈花堂景点封面",
    imageCount: 1,
  },
  "nianhuawan-nh-005": {
    attractionId: "nianhuawan-nh-005",
    name: "五灯湖",
    cover: "/assets/attractions/nianhuawan-nh-005/cover.jpg",
    samples: ["/assets/attractions/nianhuawan-nh-005/cover.jpg", "/assets/attractions/nianhuawan-nh-005/sample-1.jpg", "/assets/attractions/nianhuawan-nh-005/sample-2.jpg", "/assets/attractions/nianhuawan-nh-005/sample-3.jpg", "/assets/attractions/nianhuawan-nh-005/sample-4.jpg"],
    alt: "五灯湖景点封面",
    imageCount: 5,
  },
  "nianhuawan-nh-006": {
    attractionId: "nianhuawan-nh-006",
    name: "鹿鸣谷",
    cover: "/assets/attractions/nianhuawan-nh-006/cover.jpg",
    samples: ["/assets/attractions/nianhuawan-nh-006/cover.jpg", "/assets/attractions/nianhuawan-nh-006/sample-1.jpg", "/assets/attractions/nianhuawan-nh-006/sample-2.jpg"],
    alt: "鹿鸣谷景点封面",
    imageCount: 3,
  },
};

export function getAttractionMedia(attractionId?: string): AttractionMedia | null {
  if (!attractionId) {
    return null;
  }
  return attractionMediaById[attractionId] || null;
}

export function getAttractionCover(attractionId?: string): string | null {
  return getAttractionMedia(attractionId)?.cover || null;
}
