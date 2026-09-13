export interface Disease {
  id: string;
  name_en: string;
  name_mr: string;
  scientificName: string;
  aliases: string[];
  category: "Viral" | "Bacterial" | "Parasitic" | "Fungal" | "Nutritional" | "Zoonotic" | "Other";
  affectedSpecies: string[];
  riskLevel: "Low" | "Moderate" | "High" | "Critical";
  zoonotic: boolean;
  vaccinePreventable: boolean;
  description_en: string;
  description_mr: string;
  symptoms_en: string[];
  symptoms_mr: string[];
  transmission_en: string;
  transmission_mr: string;
  prevention_en: string;
  prevention_mr: string;
  /** Whether the disease is notifiable to state/WOAH surveillance systems. */
  notifiable?: boolean;
  /** National or state disease control programme associated with the disease. */
  programme?: string;
  /** Where the entry comes from (published reference). */
  source?: string;
}

// ---------------------------------------------------------------------------
// Published disease reference catalog for India / Maharashtra.
//
// The selection and classification follow the disease set reported by the
// Department of Animal Husbandry & Dairying (DAHD, Govt. of India) in its
// annual "Livestock Health & Disease Control" reports and the WOAH listed
// disease framework. Risk levels reflect national programme priority
// (NADCP / state control programmes) rather than case data.
// ---------------------------------------------------------------------------
const publishedDiseaseCatalog: Disease[] = [
  {
    id: "D-001",
    name_en: "Foot-and-Mouth Disease (FMD)",
    name_mr: "लाळ्या खुरकूत",
    scientificName: "Apthovirus (Picornaviridae), serotypes O, A, Asia-1",
    aliases: ["FMD", "Hoof and Mouth"],
    category: "Viral",
    affectedSpecies: ["Cattle", "Buffalo", "Pig", "Sheep", "Goat"],
    riskLevel: "Critical",
    zoonotic: false,
    vaccinePreventable: true,
    description_en: "A highly contagious viral disease of cloven-hoofed animals causing significant economic losses; India's NADCP targets eradication by 2030 through six-monthly vaccination.",
    description_mr: "खूर असलेल्या प्राण्यांचा अत्यंत सांसर्गिक विषाणूजन्य आजार ज्यामुळे मोठ्या प्रमाणात आर्थिक नुकसान होते; सहा महिन्यांआड लसीकरणाद्वारे २०३० पर्यंत निर्मूलनाचे उद्दिष्ट आहे.",
    symptoms_en: ["Fever", "Blisters in mouth and on feet", "Drop in milk production", "Lameness", "Excessive salivation"],
    symptoms_mr: ["ताप", "तोंडात आणि पायांवर फोड", "दूध उत्पादनात घट", "लंगडेपणा", "जास्त लाळ गळणे"],
    transmission_en: "Direct contact with infected animals, contaminated aerosols, equipment, and vehicles.",
    transmission_mr: "संक्रमित प्राण्यांशी थेट संपर्क, दूषित हवा, उपकरणे आणि वाहने यांच्याद्वारे.",
    prevention_en: "Strict biosecurity, movement control of infected animals, and routine biannual vaccination under NADCP.",
    prevention_mr: "कडक जैवसुरक्षा, संक्रमित प्राण्यांच्या हालचालींवर नियंत्रण आणि नियमित सहामाही लसीकरण.",
    notifiable: true,
    programme: "National Animal Disease Control Programme (NADCP)",
    source: "DAHD, Govt. of India; WOAH listed disease",
  },
  {
    id: "D-002",
    name_en: "Lumpy Skin Disease (LSD)",
    name_mr: "लंपी त्वचा रोग",
    scientificName: "Capripoxvirus (Neethling strain)",
    aliases: ["LSD", "Neethling virus"],
    category: "Viral",
    affectedSpecies: ["Cattle", "Buffalo"],
    riskLevel: "High",
    zoonotic: false,
    vaccinePreventable: true,
    description_en: "A viral disease characterized by fever, enlarged lymph nodes, and multiple skin nodules; first reported in India in 2019 and now covered by the indigenous Lumpi-ProVacInd vaccine.",
    description_mr: "ताप, वाढलेल्या लिम्फ नोड्स आणि त्वचेवर अनेक गाठी द्वारे वैशिष्ट्यीकृत विषाणूजन्य रोग; भारतात २०१९ मध्ये प्रथम आढळला असून स्वदेशी लस उपलब्ध आहे.",
    symptoms_en: ["High fever", "Nodules (2-5 cm) on skin", "Swollen lymph nodes", "Loss of appetite", "Reduced milk yield"],
    symptoms_mr: ["तीव्र ताप", "त्वचेवर गाठी (2-5 सेमी)", "सुजलेल्या लिम्फ नोड्स", "भूक न लागणे", "दुधाचे उत्पादन कमी होणे"],
    transmission_en: "Blood-feeding arthropod vectors like mosquitoes, biting flies, and ticks.",
    transmission_mr: "रक्त शोषक कीटक जसे की डास, माश्या आणि गोचीड यांच्याद्वारे.",
    prevention_en: "Vector control using insect repellents, strict quarantine of new animals, and ring vaccination around outbreak zones.",
    prevention_mr: "कीटकनाशकांचा वापर करून कीटक नियंत्रण, नवीन प्राण्यांचे कडक अलगीकरण आणि प्रादुर्भाव क्षेत्राभोवती लसीकरण.",
    notifiable: true,
    programme: "LSD Control Programme (DAHD)",
    source: "DAHD, Govt. of India; WOAH listed disease",
  },
  {
    id: "D-003",
    name_en: "Brucellosis",
    name_mr: "ब्रुसेलोसिस (संसर्गजन्य गर्भपात)",
    scientificName: "Brucella abortus / Brucella melitensis",
    aliases: ["Contagious Abortion", "Bang's Disease"],
    category: "Zoonotic",
    affectedSpecies: ["Cattle", "Buffalo", "Sheep", "Goat", "Pig"],
    riskLevel: "High",
    zoonotic: true,
    vaccinePreventable: true,
    description_en: "A highly contagious zoonotic infection causing reproductive failures and significant public health concerns; NADCP vaccinates female bovine calves aged 4-8 months.",
    description_mr: "एक अत्यंत सांसर्गिक झुनोटिक संसर्ग ज्यामुळे प्रजनन अपयश आणि महत्त्वपूर्ण सार्वजनिक आरोग्य समस्या निर्माण होतात; ४-८ महिन्यांच्या मादी वासरांचे लसीकरण केले जाते.",
    symptoms_en: ["Abortion during late pregnancy", "Retained placenta", "Infertility", "Joint pain/swelling"],
    symptoms_mr: ["गर्भधारणेच्या उत्तरार्धात गर्भपात", "वार अडकणे", "वंध्यत्व", "सांधेदुखी/सूज"],
    transmission_en: "Ingestion of contaminated feed/water, direct contact with aborted fetuses, and venereal transmission.",
    transmission_mr: "दूषित चारा/पाणी ग्रहण करणे, गर्भपात झालेल्या गर्भाशी थेट संपर्क आणि वीर्याद्वारे प्रसार.",
    prevention_en: "Calfhood vaccination, testing and culling of positive animals, and use of protective gear by handlers.",
    prevention_mr: "वासरांचे लसीकरण, बाधित प्राण्यांची तपासणी करून विल्हेवाट लावणे आणि हाताळणाऱ्यांकडून संरक्षणात्मक उपकरणांचा वापर.",
    notifiable: true,
    programme: "National Animal Disease Control Programme (NADCP)",
    source: "DAHD, Govt. of India; WOAH listed disease",
  },
  {
    id: "D-004",
    name_en: "Peste des Petits Ruminants (PPR)",
    name_mr: "पीपीआर (शेळ्या-मेंढ्यांचा प्लेग)",
    scientificName: "Small ruminant morbillivirus",
    aliases: ["PPR", "Goat Plague", "Ovine Rinderpest"],
    category: "Viral",
    affectedSpecies: ["Sheep", "Goat"],
    riskLevel: "High",
    zoonotic: false,
    vaccinePreventable: true,
    description_en: "A severe, fast-spreading viral disease of sheep and goats characterized by high morbidity and mortality; India runs a national eradication programme targeting 2030.",
    description_mr: "शेळ्या आणि मेंढ्यांचा एक गंभीर, वेगाने पसरणारा विषाणूजन्य आजार ज्यामध्ये मृत्यूचे प्रमाण जास्त असते; २०३० पर्यंत निर्मूलनासाठी राष्ट्रीय कार्यक्रम सुरू आहे.",
    symptoms_en: ["High fever", "Discharge from eyes and nose", "Sores in mouth", "Severe diarrhea", "Pneumonia"],
    symptoms_mr: ["तीव्र ताप", "डोळे आणि नाकातून स्त्राव", "तोंडात फोड", "तीव्र अतिसार", "न्यूमोनिया"],
    transmission_en: "Direct contact with infected animals, especially through respiratory secretions and feces.",
    transmission_mr: "संक्रमित प्राण्यांशी थेट संपर्क, विशेषत: श्वासोच्छवासाचे स्त्राव आणि विष्ठेद्वारे.",
    prevention_en: "Mass vaccination campaigns, isolation of sick animals, and safe disposal of carcasses.",
    prevention_mr: "सामूहिक लसीकरण मोहिमा, आजारी प्राण्यांचे अलगीकरण आणि मृतदेहांची सुरक्षित विल्हेवाट.",
    notifiable: true,
    programme: "National PPR Eradication Programme (target 2030)",
    source: "DAHD, Govt. of India; WOAH listed disease",
  },
  {
    id: "D-005",
    name_en: "Hemorrhagic Septicemia (HS)",
    name_mr: "गळघोटू",
    scientificName: "Pasteurella multocida (serotypes B:2, E:2)",
    aliases: ["HS", "Galghotu", "Shipping Fever"],
    category: "Bacterial",
    affectedSpecies: ["Cattle", "Buffalo"],
    riskLevel: "High",
    zoonotic: false,
    vaccinePreventable: true,
    description_en: "An acute, often fatal bacterial septicaemia of cattle and buffaloes that flares up during the rainy season; it is one of the most economically important diseases of bovines in India.",
    description_mr: "पावसाळ्यात उद्रेक होणारा गुरा-म्हशींचा तीव्र आणि अनेकदा घातक जिवाणूजन्य संसर्ग; हा भारतातील आर्थिकदृष्ट्या महत्त्वाच्या आजारांपैकी एक आहे.",
    symptoms_en: ["Sudden high fever", "Swelling of throat and dewlap", "Difficulty breathing", "Drooling", "Death within 24-48 hours in acute cases"],
    symptoms_mr: ["अचानक तीव्र ताप", "घसा आणि गळ्याखाली सूज", "श्वास घेण्यास त्रास", "लाळ गळणे", "तीव्र अवस्थेत २४-४८ तासांत मृत्यू"],
    transmission_en: "Ingestion of contaminated feed and water; carrier animals shed bacteria during stressful conditions such as monsoon.",
    transmission_mr: "दूषित चारा आणि पाण्याद्वारे प्रसार; तणावाच्या काळात वाहक प्राण्यांद्वारे जिवाणू पसरतात.",
    prevention_en: "Annual pre-monsoon vaccination (April-May), good drainage of grazing areas, and prompt antibiotic treatment of early cases.",
    prevention_mr: "वार्षिक पावसाळ्यापूर्वी लसीकरण (एप्रिल-मे), कुरणांचे योग्य पाण्याचे निचरे आणि सुरुवातीच्या अवस्थेत जलद प्रतिजैविक उपचार.",
    notifiable: false,
    programme: "State Livestock Health Programme",
    source: "DAHD annual Livestock Health & Disease Control reports",
  },
  {
    id: "D-006",
    name_en: "Blackquarter (BQ)",
    name_mr: "ब्लॅकक्वार्टर",
    scientificName: "Clostridium chauvoei",
    aliases: ["BQ", "Blackleg", "Quarter evil"],
    category: "Bacterial",
    affectedSpecies: ["Cattle", "Sheep", "Goat"],
    riskLevel: "Moderate",
    zoonotic: false,
    vaccinePreventable: true,
    description_en: "A soil-borne clostridial infection causing emphysematous swelling and necrosis of muscles, mainly in young, well-conditioned cattle; spores persist in soil for years.",
    description_mr: "मातीतील जिवाणूंमुळे होणारा संसर्ग ज्यात स्नायूंची सूज आणि मृत्यू होतो; मुख्यत: चांगल्या स्थितीतील तरुण गुरांमध्ये आढळतो.",
    symptoms_en: ["Fever", "Hot painful swelling over large muscles", "Crepitation (crackling) on pressing swelling", "Lameness", "Sudden death"],
    symptoms_mr: ["ताप", "मोठ्या स्नायूंवर गरम वेदनादायक सूज", "सूजेवर दाबल्यास करकर आवाज", "लंगडेपणा", "अचानक मृत्यू"],
    transmission_en: "Ingestion of spores from contaminated soil or feed, especially after soil disturbance or flooding.",
    transmission_mr: "दूषित माती किंवा चाऱ्यातील बीजाणू ग्रहण केल्याने प्रसार होतो, विशेषत: पूर आल्यानंतर.",
    prevention_en: "Annual vaccination in endemic pockets and safe disposal of carcasses to prevent soil contamination.",
    prevention_mr: "स्थानिक पातळीवरील क्षेत्रात वार्षिक लसीकरण आणि माती दूषित होऊ नये म्हणून मृतदेहांची सुरक्षित विल्हेवाट.",
    notifiable: false,
    programme: "State Livestock Health Programme",
    source: "DAHD annual Livestock Health & Disease Control reports",
  },
  {
    id: "D-007",
    name_en: "Anthrax",
    name_mr: "ॲन्थ्रॅक्स",
    scientificName: "Bacillus anthracis",
    aliases: ["Splenic fever"],
    category: "Zoonotic",
    affectedSpecies: ["Cattle", "Buffalo", "Sheep", "Goat"],
    riskLevel: "High",
    zoonotic: true,
    vaccinePreventable: true,
    description_en: "A peracute to acute zoonotic infection caused by spore-forming Bacillus anthracis; endemic pockets exist in Maharashtra and outbreaks are notifiable to the state.",
    description_mr: "बीजाणू तयार करणाऱ्या जिवाणूंमुळे होणारा तीव्र झुनोटिक संसर्ग; महाराष्ट्रात स्थानिक क्षेत्रे असून प्रादुर्भाव राज्याला कळवणे बंधनकारक आहे.",
    symptoms_en: ["Sudden high fever", "Difficulty breathing", "Blood oozing from natural orifices", "Rigidity after death", "Sudden death"],
    symptoms_mr: ["अचानक तीव्र ताप", "श्वास घेण्यास त्रास", "शरीराच्या छिद्रांतून रक्तस्राव", "मृत्यूनंतर शरीराची कडक होणे", "अचानक मृत्यू"],
    transmission_en: "Ingestion or inhalation of spores from contaminated soil, feed or carcasses; spores survive for decades.",
    transmission_mr: "दूषित माती, चारा किंवा मृतदेहांतील बीजाणू ग्रहण केल्याने किंवा श्वासोच्छवासाद्वारे प्रसार होतो.",
    prevention_en: "Annual vaccination in endemic areas; carcasses must be buried or burnt without opening; handlers must use protective equipment.",
    prevention_mr: "स्थानिक क्षेत्रात वार्षिक लसीकरण; मृतदेह न उघडता पुरणे किंवा जाळणे; हाताळणाऱ्यांनी संरक्षणात्मक साधने वापरणे.",
    notifiable: true,
    programme: "State surveillance; One Health framework with public health department",
    source: "DAHD, Govt. of India; WOAH listed disease",
  },
  {
    id: "D-008",
    name_en: "Rabies",
    name_mr: "रेबीज",
    scientificName: "Lyssavirus (Rhabdoviridae)",
    aliases: ["Hydrophobia"],
    category: "Zoonotic",
    affectedSpecies: ["Cattle", "Buffalo", "Goat", "Sheep"],
    riskLevel: "Critical",
    zoonotic: true,
    vaccinePreventable: true,
    description_en: "A fatal zoonotic viral encephalitis transmitted through bites; livestock cases are usually linked to dog-mediated transmission. India targets rabies elimination by 2030.",
    description_mr: "चावण्याद्वारे पसरणारा घातक झुनोटिक विषाणूजन्य मेंदूदाह; गुरांमधील संसर्ग बहुधा कुत्र्यांमुळे होतो. भारत २०३० पर्यंत निर्मूलनाचे उद्दिष्ट ठेवतो.",
    symptoms_en: ["Behavioural change (dumb or furious form)", "Excessive salivation", "Difficulty swallowing", "Incoordination", "Paralysis and death"],
    symptoms_mr: ["वर्तनात बदल", "जास्त लाळ गळणे", "गिळण्यास त्रास", "तोल जाणे", "पक्षाघात आणि मृत्यू"],
    transmission_en: "Bite of an infected animal, most commonly dogs; virus present in saliva.",
    transmission_mr: "बाधित प्राण्याच्या (बहुधा कुत्र्याच्या) चाव्याद्वारे; विषाणू लाळेमध्ये असतो.",
    prevention_en: "Post-bite wound washing and immediate human anti-rabies vaccination; annual vaccination of dogs and at-risk livestock.",
    prevention_mr: "चावल्यानंतर जखम धुणे आणि त्वरित लसीकरण; कुत्री आणि जोखीम असलेल्या गुरांचे वार्षिक लसीकरण.",
    notifiable: true,
    programme: "National Action Plan for Rabies Elimination (NAPRE)",
    source: "DAHD / Ministry of Health & Family Welfare, Govt. of India",
  },
  {
    id: "D-009",
    name_en: "Theileriosis",
    name_mr: "थिलेरियोसिस",
    scientificName: "Theileria annulata",
    aliases: ["Tropical theileriosis", "Mediterranean coast fever"],
    category: "Parasitic",
    affectedSpecies: ["Cattle", "Buffalo"],
    riskLevel: "Moderate",
    zoonotic: false,
    vaccinePreventable: false,
    description_en: "A tick-borne protozoan disease causing fever, enlarged lymph nodes and anaemia; it is a major constraint for crossbred and exotic cattle in India.",
    description_mr: "गोचडीमुळे पसरणारा जिवाणूजन्य आजार ज्यात ताप, गाठी आणि रक्तक्षय होतो; संकरित गुरांसाठी मोठा अडथळा.",
    symptoms_en: ["High fever", "Enlarged lymph nodes", "Anaemia", "Drop in milk yield", "Weakness"],
    symptoms_mr: ["तीव्र ताप", "सुजलेल्या लिम्फ नोड्स", "रक्तक्षय", "दूध उत्पादनात घट", "कमकुवतपणा"],
    transmission_en: "Through the bite of infected Hyalomma ticks.",
    transmission_mr: "बाधित हयालोमा गोचडीच्या चाव्याद्वारे.",
    prevention_en: "Regular tick control (acaricides, fodder management), housing hygiene and treatment with buparvaquone in early cases.",
    prevention_mr: "नियमित गोचीड नियंत्रण, निवारा स्वच्छता आणि सुरुवातीच्या अवस्थेत योग्य औषधोपचार.",
    notifiable: false,
    programme: "State veterinary services",
    source: "ICAR / DAHD disease literature",
  },
  {
    id: "D-010",
    name_en: "Mastitis",
    name_mr: "कासदाह",
    scientificName: "Staphylococcus spp., Streptococcus spp., Escherichia coli and others",
    aliases: ["Udder infection"],
    category: "Bacterial",
    affectedSpecies: ["Cattle", "Buffalo"],
    riskLevel: "Moderate",
    zoonotic: false,
    vaccinePreventable: false,
    description_en: "Inflammation of the udder caused by bacteria entering through the teat canal; it is the single largest production disease of dairy animals in India in economic terms.",
    description_mr: "दुधाच्या ग्रंथींमध्ये जिवाणूंच्या संसर्गामुळे होणारी सूज; भारतातील दुभत्या जनावरांमधील आर्थिकदृष्ट्या सर्वात मोठा उत्पादन आजार.",
    symptoms_en: ["Swollen, painful udder", "Watery or clotted milk", "Fever in acute cases", "Drop in milk yield"],
    symptoms_mr: ["सूजलेले, दुखणारे कास", "पातळ किंवा घट्ट दूध", "तीव्र अवस्थेत ताप", "दूध उत्पादनात घट"],
    transmission_en: "Mainly through contaminated milking hands, machines and wet, unhygienic housing.",
    transmission_mr: "मुख्यत: दूषित हात, दुग्ध यंत्रांमुळे आणि अस्वच्छ निवाऱ्याद्वारे.",
    prevention_en: "Hygienic milking, teat dipping, dry-cow therapy and clean dry bedding.",
    prevention_mr: "स्वच्छ दुग्धन, टीट डिपिंग, ड्राय-काऊ थेरपी आणि कोरडी स्वच्छ निवारा व्यवस्था.",
    notifiable: false,
    programme: "Dairy extension programmes",
    source: "ICAR-NDRI / DAHD extension literature",
  },
  {
    id: "D-011",
    name_en: "Avian Influenza (Bird Flu)",
    name_mr: "ॲव्हियन इन्फ्लुएंझा (बर्ड फ्लू)",
    scientificName: "Influenza A virus (H5N1 and other subtypes)",
    aliases: ["Bird Flu", "HPAI"],
    category: "Zoonotic",
    affectedSpecies: ["Poultry"],
    riskLevel: "Critical",
    zoonotic: true,
    vaccinePreventable: false,
    description_en: "A highly contagious viral infection of birds with public-health significance; India follows an AOI-based culling and containment policy rather than vaccination.",
    description_mr: "पक्ष्यांचा अत्यंत सांसर्गिक विषाणूजन्य आजार ज्याचा सार्वजनिक आरोग्यावर परिणाम होतो; भारत लसीकरणाऐवजी नियंत्रण क्षेत्रातील कलिंग धोरण पाळतो.",
    symptoms_en: ["Sudden high mortality in flocks", "Swollen head and comb", "Respiratory distress", "Drop in egg production", "Neurological signs"],
    symptoms_mr: ["कळपात अचानक जास्त मृत्यू", "डोके आणि कांबा सूजणे", "श्वास घेण्यास त्रास", "अंडी उत्पादनात घट", "मज्जासंस्थेची लक्षणे"],
    transmission_en: "Contact with infected birds, their droppings, and contaminated equipment; wild migratory birds can introduce the virus.",
    transmission_mr: "बाधित पक्षी, त्यांची विष्ठा आणि दूषित उपकरणांशी संपर्क; स्थलांतरित पक्ष्यांद्वारे विषाणू येऊ शकतो.",
    prevention_en: "Biosecurity on farms, movement restrictions, surveillance of migratory birds and immediate reporting of unusual mortality.",
    prevention_mr: "शेतांवर जैवसुरक्षा, वाहतूक निर्बंध, स्थलांतरित पक्ष्यांवर लक्ष आणि असामान्य मृत्यूची त्वरित नोंद.",
    notifiable: true,
    programme: "Action Plan for Prevention, Control and Containment of Avian Influenza (DAHD)",
    source: "DAHD, Govt. of India; WOAH listed disease",
  },
  {
    id: "D-012",
    name_en: "Ranikhet Disease (Newcastle Disease)",
    name_mr: "रानिखेत रोग (न्यूकॅसल)",
    scientificName: "Avian orthoavulavirus 1",
    aliases: ["Newcastle Disease", "ND"],
    category: "Viral",
    affectedSpecies: ["Poultry"],
    riskLevel: "High",
    zoonotic: false,
    vaccinePreventable: true,
    description_en: "A highly contagious viral disease of poultry causing respiratory, nervous and digestive signs; controlled in India by the F1/R2B vaccination schedule.",
    description_mr: "कोंबड्यांमधील अत्यंत सांसर्गिक विषाणूजन्य आजार; श्वसन, मज्जासंस्था आणि पाचन संस्थेवर परिणाम करतो; लसीकरणाद्वारे नियंत्रित केला जातो.",
    symptoms_en: ["Respiratory distress", "Twisted neck (torticollis)", "Greenish diarrhea", "Drop in egg production", "High mortality in chicks"],
    symptoms_mr: ["श्वास घेण्यास त्रास", "मान वाकणे", "हिरवट अतिसार", "अंडी उत्पादनात घट", "पिलांमध्ये जास्त मृत्यू"],
    transmission_en: "Inhalation or ingestion of virus from droppings and secretions of infected birds.",
    transmission_mr: "बाधित पक्ष्यांच्या विष्ठा आणि स्रावातील विषाणू श्वास किंवा आहाराद्वारे ग्रहण केल्याने.",
    prevention_en: "F1 vaccination of day-old chicks followed by R2B/LaSota boosters, plus strict flock biosecurity.",
    prevention_mr: "दिवसभराच्या पिलांना प्राथमिक लस आणि त्यानंतर बूस्टर लस, तसेच कळपाची जैवसुरक्षा.",
    notifiable: true,
    programme: "Poultry Disease Control Programme",
    source: "DAHD / ICAR; WOAH listed disease",
  },
  {
    id: "D-013",
    name_en: "Goat Pox and Sheep Pox",
    name_mr: "शेळ्या-मेंढ्यांचा चेचक",
    scientificName: "Capripoxvirus (goat/sheep strains)",
    aliases: ["Goat Pox", "Sheep Pox"],
    category: "Viral",
    affectedSpecies: ["Goat", "Sheep"],
    riskLevel: "Moderate",
    zoonotic: false,
    vaccinePreventable: true,
    description_en: "A contagious viral disease causing fever and pox lesions on skin and internal organs of small ruminants; vaccination is advised in endemic tracts.",
    description_mr: "शेळ्या-मेंढ्यांमध्ये ताप आणि त्वचेवर चेचक पुरळ निर्माण करणारा सांसर्गिक आजार; स्थानिक क्षेत्रात लसीकरण आवश्यक.",
    symptoms_en: ["Fever", "Pox lesions on skin and mucous membranes", "Discharge from eyes and nose", "Loss of appetite", "High mortality in kids/lambs"],
    symptoms_mr: ["ताप", "त्वचा आणि श्लेष्मल पटलावर चेचक पुरळ", "डोळे व नाकातून स्त्राव", "भूक न लागणे", "पिलांमध्ये जास्त मृत्यू"],
    transmission_en: "Inhalation of aerosols and direct contact with lesions or contaminated sheds.",
    transmission_mr: "हवेतील कणांच्या श्वासोच्छवासाद्वारे आणि जखमा किंवा दूषित निवाऱ्याशी थेट संपर्काने.",
    prevention_en: "Annual vaccination in endemic areas, isolation of cases and disinfection of sheds.",
    prevention_mr: "स्थानिक क्षेत्रात वार्षिक लसीकरण, आजारी प्राण्यांचे अलगीकरण आणि निवाऱ्यांची निर्जंतुकीकरण.",
    notifiable: true,
    programme: "State Livestock Health Programme",
    source: "DAHD annual Livestock Health & Disease Control reports",
  },
  {
    id: "D-014",
    name_en: "Classical Swine Fever (CSF)",
    name_mr: "क्लासिकल स्वाईन फीवर (डुकरांचा ताप)",
    scientificName: "Classical swine fever virus (Pestivirus)",
    aliases: ["CSF", "Hog Cholera"],
    category: "Viral",
    affectedSpecies: ["Pig"],
    riskLevel: "High",
    zoonotic: false,
    vaccinePreventable: true,
    description_en: "A severe, highly contagious viral disease of pigs with high mortality; India runs control programmes based on the lapinised vaccine.",
    description_mr: "डुकरांमधील तीव्र सांसर्गिक विषाणूजन्य आजार ज्यात मृत्यूचे प्रमाण जास्त असते; लसीकरणावर आधारित नियंत्रण कार्यक्रम सुरू आहे.",
    symptoms_en: ["High fever", "Loss of appetite", "Skin haemorrhages", "Constipation followed by diarrhea", "High mortality"],
    symptoms_mr: ["तीव्र ताप", "भूक न लागणे", "त्वचेवर रक्तस्रावाचे डाग", "बद्धकोष्ठतेनंतर अतिसार", "जास्त मृत्यू"],
    transmission_en: "Direct contact with infected pigs and contaminated feed (especially uncooked swill).",
    transmission_mr: "बाधित डुकरांशी थेट संपर्क आणि दूषित चारा (विशेषत: न उकळलेले उरलेले अन्न) यांद्वारे.",
    prevention_en: "Annual vaccination, banning swill feeding and strict quarantine of purchased animals.",
    prevention_mr: "वार्षिक लसीकरण, उरलेले अन्न खाऊ घालण्यास मनाई आणि खरेदी केलेल्या प्राण्यांचे अलगीकरण.",
    notifiable: true,
    programme: "State Livestock Health Programme",
    source: "DAHD annual Livestock Health & Disease Control reports",
  },
];

export const DiseaseService = {
  async getDiseases(): Promise<Disease[]> {
    return new Promise((resolve) => setTimeout(() => resolve(publishedDiseaseCatalog), 300));
  },
  async searchDiseases(query: string, category: string, riskLevel: string, species: string): Promise<Disease[]> {
    return new Promise((resolve) => setTimeout(() => {
      let filtered = publishedDiseaseCatalog;
      if (query) {
        const q = query.toLowerCase();
        filtered = filtered.filter(d =>
          d.name_en.toLowerCase().includes(q) ||
          d.name_mr.includes(q) ||
          d.aliases.some(a => a.toLowerCase().includes(q))
        );
      }
      if (category && category !== "All") {
        filtered = filtered.filter(d => d.category === category);
      }
      if (riskLevel && riskLevel !== "All") {
        filtered = filtered.filter(d => d.riskLevel === riskLevel);
      }
      if (species && species !== "All") {
        filtered = filtered.filter(d => d.affectedSpecies.includes(species));
      }
      resolve(filtered);
    }, 300));
  }
};
