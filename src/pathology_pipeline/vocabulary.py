"""
Closed vocabulary for the "Other" (code 99) histology category.

Findings matching one of these terms are coded as "Other" rather than forced into
the closest-sounding numbered category (see rule 10 in prompt.py). This list mirrors
the terminology used by trained research assistants when entering free-text "Other,
specify" findings during manual reference-standard coding.
"""

OTHER_VOCABULARY = (
    "architectural disorganization (light or full), active chronic colitis, "
    "active focal inflammation, apoptotic bodies in the crypts, basal hyperplasia, "
    "celiac disease, chronic active ileitis (mild or severe), chronic active "
    "ileitis-colitis (mild, at anastomosis), chronic active rectitis "
    "(moderate-to-severe or severe), chronic bulbitis, chronic duodenitis, "
    "congestive rectal mucosa, congestive gastropathy, cryptal hyperplasia, "
    "cystic dilation, discrete increase in inflammatory contingent, discrete "
    "non-reactive chronic inflammatory infiltrate, duodenitis, endocrine "
    "hyperplasia, erosion, esophagitis, exudation, fibrin cap, focal active "
    "colitis, focal active ileitis, focal acute colitis, foveolar hyperplasia, "
    "granulation tissue, gastric foveolar metaplasia, gastric heterotopia, "
    "glandular rupture, hamartomatous polyp, Helicobacter pylori (H. pylori), "
    "hypertrophy of muscularis mucosae, inactive chronic ileitis-colitis (at "
    "anastomosis), inactive chronic inflammation, insufficient tissue for "
    "diagnosis, intestinal metaplasia, "
    "intraepithelial neutrophils and eosinophils, irregular thickening of the "
    "basal lamina, leiomyoma of the muscularis mucosae, low-grade follicular "
    "lymphoma, lymphangiectasia, lymphangioma, lymphocytic colitis, lymphoid "
    "aggregate, lymphoid follicle, lymphoid hyperplasia, mild ischemic colitis, "
    "mild eosinophilia in the chorion, mononuclear inflammation, mucosal colitis, "
    "neuroendocrine proliferation, neuroendocrine tumor (G1), parakeratosis, "
    "peptic damage, Peyer's patch, post-radiation changes, pouchitis, "
    "pseudomelanosis, pseudopyloric extensive metaplasia, secondary enteropathy "
    "(e.g. Olmesartan-associated)."
)
