# MP2 Reflection

## What worked
Usage of keyword search (BM25) and fuse ranking, as dense search was bring-in noise for ceratin queries.

## What didn't work
Pure dense vector search (`text-embedding-3-small`) consistently struggled with queries containing exact-match keywords. Dense retrieval returned semantically similar than the exact line context required, leading to hallucinated or overly broad answer context. Also relevancy of the answer is still a question.
Also Rerank failed - it didn't bring in the relevant results for the questions, with rerank the `Chunk-match` was `6/10`, whereas **without rerank** the `Chunk-match` was `8/10` 

## What I'd change
Maybe the chunking strategy to go by pages/ topics rather than fixed characters. 
Maybe I'll try with other models


## One surprise
Actual surprise for me was the rag-pipeline code that I had build on my data set was supporting to complete the project pipeline witin 30 minutes.
Also the response from ask_rag surprised me when it returned with clear/ precise answer, except for the hallucinated question that was meant by purpose
But I was expecting rerank using Cross encoder to bring better results, but unfortunately I got better results without Cross encoder.


# Match results:
## Without rerank:
  **Predefined questions** Source match = 2/2, Chunk match 2/2
  **10 learner questions** Source match = 9/10, Chunk match 8/10 `one question is hallucinated`
## With rerank:
  **Predefined questions** Source match = 2/2, Chunk match 1/2
  **10 learner questions** Source match = 9/10, Chunk match 6/10 `one question is hallucinated`


# Results:
## ========================================================================================== ##
python mp2_rag.py validate
Connected to Qdrant at https://91ecc16f-269a-4046-b44c-5a190057...
Rerank required?: FalseFalse

  Validating 2 questions from predefined_questions.jsonl…



  ✓✓ q1_red_headed_league_assistant
      Q: Who was the assistant working at Jabez Wilson's pawnshop, and what was his real identity?
      Cited: 01_red_headed_league.txt | Chunks: {'01_red_headed_league.txt#3', '01_red_headed_league.txt#7', '01_red_headed_league.txt#5', '01_red_headed_league.txt#0', '01_red_headed_league.txt#4'}
      Expected: 01_red_headed_league.txt | Expected chunks: 01_red_headed_league.txt#3
      Facts matched: 2/5
      Latency: 1.0791225339926314s
      Answer: The assistant working at Jabez Wilson's pawnshop was Vincent Spaulding. His real identity is John Clay, the grandson of a royal duke and one of the most cunning thieves in London (The Red-Headed League, The Identity of the Assistant).
      Expected ans: ['Vincent Spaulding', 'John Clay', 'thief', 'wanted for murder, theft, smashing and forgery', 'white patches on his trouser knees']



  ✓✓ q2_speckled_band_murder_weapon
      Q: What killed Julia Stoner at Stoke Moran, and how was the method discovered?
      Cited: 02_speckled_band.txt | Chunks: {'02_speckled_band.txt#6', '02_speckled_band.txt#7', '02_speckled_band.txt#3', '02_speckled_band.txt#1', '02_speckled_band.txt#0'}
      Expected: 02_speckled_band.txt | Expected chunks: ['02_speckled_band.txt#1', '02_speckled_band.txt#3']
      Facts matched: 0/6
      Latency: 1.5550146299938206s
      Answer: The cause of Julia Stoner's death was never determined, as the coroner could find no cause of death, no poison, no wound, and no struggle. The door had been locked from the inside, and the shutters were closed and barred (source: The Adventure of the Speckled Band, section 6). The method of her death was discovered later by Sherlock Holmes during his investigation, but the excerpts provided do not specify what that method was.
      Expected ans: ['swamp adder', 'snake', 'ventilator', 'bell-rope', 'Doctor Roylott', 'trained the snake']

  Source-match: 2/2
  Chunk-match 2/2

## ------------------------------------------------------------------------------------------ ##


  Validating 10 questions from learner_questions.jsonl…



  ✓✓ g001
      Q: What was Jabez Wilson's occupation and primary distinguishing physical trait?
      Cited: 02_speckled_band.txt, 01_red_headed_league.txt | Chunks: {'01_red_headed_league.txt#2', '01_red_headed_league.txt#3', '01_red_headed_league.txt#8', '01_red_headed_league.txt#0', '02_speckled_band.txt#3'}
      Expected: 01_red_headed_league.txt | Expected chunks: ['01_red_headed_league.txt#0']
      Facts matched: 2/3
      Latency: 0.9512767429987434s
      Answer: Jabez Wilson was a pawnbroker, and his primary distinguishing physical trait was his head of brilliantly red hair. (The Red-Headed League, section 0)
      Expected ans: ['pawnbroker', 'Coburg Square', 'brilliantly red hair']



  ✓✓ g002
      Q: Where did Helen Stoner travel from on her early morning visit to Baker Street?
      Cited: 05_scandal_in_bohemia.txt, 02_speckled_band.txt | Chunks: {'05_scandal_in_bohemia.txt#5', '02_speckled_band.txt#7', '02_speckled_band.txt#3', '02_speckled_band.txt#4', '02_speckled_band.txt#0'}
      Expected: 02_speckled_band.txt | Expected chunks: ['02_speckled_band.txt#0']
      Facts matched: 1/3
      Latency: 0.8944133960176259s
      Answer: Helen Stoner traveled from Leatherhead in Surrey on her early morning visit to Baker Street. (The Adventure of the Speckled Band, Context)
      Expected ans: ['Leatherhead in Surrey', 'dog-cart and train', 'Stoke Moran']



  ✓✓ g003
      Q: Who was initially arrested for stealing the Countess of Morcar's blue carbuncle?
      Cited: 03_blue_carbuncle.txt, 05_scandal_in_bohemia.txt | Chunks: {'03_blue_carbuncle.txt#4', '05_scandal_in_bohemia.txt#2', '03_blue_carbuncle.txt#3', '03_blue_carbuncle.txt#5', '03_blue_carbuncle.txt#12'}
      Expected: 03_blue_carbuncle.txt | Expected chunks: ['03_blue_carbuncle.txt#5']
      Facts matched: 2/4
      Latency: 0.9303283829940483s
      Answer: John Horner, a plumber who had been called to repair the grate in the Countess's dressing-room on the day of the theft, was initially arrested for stealing the Countess of Morcar's blue carbuncle. (The Blue Carbuncle, section 5)
      Expected ans: ['John Horner', 'plumber', 'Hotel Cosmopolitan', 'previous conviction']



  ✓✓ g004
      Q: Why did Colonel Stark require the carriage windows to be blinded during Hatherley's journey?
      Cited: 04_engineers_thumb.txt | Chunks: {'04_engineers_thumb.txt#6', '04_engineers_thumb.txt#4', '04_engineers_thumb.txt#8', '04_engineers_thumb.txt#5', '04_engineers_thumb.txt#3'}
      Expected: 04_engineers_thumb.txt | Expected chunks: ['04_engineers_thumb.txt#3']
      Facts matched: 2/4
      Latency: 0.9970830880047288s
      Answer: Colonel Stark required the carriage windows to be blinded so that Hatherley could not see the route to the country house called Eyford. This was part of the conditions for the job, which included complete secrecy. (The Engineer's Thumb + section 3)
      Expected ans: ['blinded windows', 'prevent seeing the route', 'secrecy', 'Eyford']



  ✓✓ g005
      Q: In what year and state was Irene Adler born?
      Cited: 05_scandal_in_bohemia.txt, 04_engineers_thumb.txt | Chunks: {'05_scandal_in_bohemia.txt#13', '05_scandal_in_bohemia.txt#10', '05_scandal_in_bohemia.txt#3', '04_engineers_thumb.txt#1', '05_scandal_in_bohemia.txt#11'}
      Expected: 05_scandal_in_bohemia.txt | Expected chunks: ['05_scandal_in_bohemia.txt#3']
      Facts matched: 2/3
      Latency: 0.6554657290107571s
      Answer: Irene Adler was born in the year 1858 in New Jersey. (A Scandal in Bohemia, section 3)
      Expected ans: ['New Jersey', '1858', 'American opera contralto']



  ✓✓ g006
      Q: What rationale did Vincent Spaulding give Jabez Wilson for spending extensive time alone in the pawnshop's cellar?
      Cited: 01_red_headed_league.txt | Chunks: {'01_red_headed_league.txt#3', '01_red_headed_league.txt#5', '01_red_headed_league.txt#6', '01_red_headed_league.txt#1', '01_red_headed_league.txt#4'}
      Expected: 01_red_headed_league.txt | Expected chunks: ['01_red_headed_league.txt#5']
      Facts matched: 1/3
      Latency: 0.925699555024039s
      Answer: Vincent Spaulding explained to Jabez Wilson that he had a fondness for photography and spent much time in the cellar developing pictures. (The Red-Headed League, section 5)
      Expected ans: ['developing photographs', 'fondness for photography', 'cellar darkroom']



  ✓✓ g007
      Q: How much money did Colonel Lysander Stark offer Victor Hatherley for his services?
      Cited: 04_engineers_thumb.txt | Chunks: {'04_engineers_thumb.txt#2', '04_engineers_thumb.txt#6', '04_engineers_thumb.txt#9', '04_engineers_thumb.txt#5', '04_engineers_thumb.txt#3'}
      Expected: 04_engineers_thumb.txt | Expected chunks: ['04_engineers_thumb.txt#3']
      Facts matched: 2/3
      Latency: 1.2735699549957644s
      Answer: Colonel Lysander Stark offered Victor Hatherley fifty guineas for a single evening's work (The Engineer's Thumb, section 3).
      Expected ans: ['fifty guineas', "single evening's work", 'three conditions']



  ✓✗ g008
      Q: How did Victor Hatherley's observation inside the hydraulic press chamber contradict Colonel Stark's explanation, and what did Holmes discover had happened to the property at Beechmoor?
      Cited: 04_engineers_thumb.txt | Chunks: {'04_engineers_thumb.txt#6', '04_engineers_thumb.txt#7', '04_engineers_thumb.txt#12', '04_engineers_thumb.txt#8', '04_engineers_thumb.txt#13'}
      Expected: 04_engineers_thumb.txt | Expected chunks: ['04_engineers_thumb.txt#8', '04_engineers_thumb.txt#11', '04_engineers_thumb.txt#12']
      Facts matched: 0/4
      Latency: 1.7309154650138225s
      Answer: Victor Hatherley's observation inside the hydraulic press chamber contradicted Colonel Stark's explanation because Hatherley noted that the floor of the press chamber was marked by a metallic crust, not by the residue of earth, which would be expected if the press had been used for compressing fuller's earth. This indicated that the press was not being used for its stated purpose. 

Holmes discovered that the property at Beechmoor had been set ablaze to destroy the evidence of the counterfeiting operation, which included the hydraulic press and the secret stamping floor. The fire was a deliberate act to eliminate any traces of the illegal activities taking place there (source: "The Engineer's Thumb" + sections 12 and 13).
      Expected ans: ["fuller's earth cover story", 'metallic crust on floor', 'Beechmoor set ablaze', 'destroy evidence']



  ✓✓ g009
      Q: How did Doctor Roylott train the snake to carry out his murder plot and return to his room?
      Cited: 02_speckled_band.txt, 01_red_headed_league.txt | Chunks: {'01_red_headed_league.txt#2', '02_speckled_band.txt#11', '02_speckled_band.txt#12', '02_speckled_band.txt#9', '02_speckled_band.txt#13'}
      Expected: 02_speckled_band.txt | Expected chunks: ['02_speckled_band.txt#12']
      Facts matched: 0/3
      Latency: 1.0432946550135966s
      Answer: Doctor Roylott trained the snake to climb the bell-rope through the ventilator and back. He whistled to call it home and rewarded it with milk. This method allowed the snake to return to his room after it had bitten Julia. (The Adventure of the Speckled Band, The Explanation)
      Expected ans: ['low whistle', 'saucer of milk', 'ventilator and bell-rope']



  ✗✗ g010
      Q: How much ransom did Professor Moriarty demand to return the stolen crown jewels in Berkshire?
      Cited: 01_red_headed_league.txt, 03_blue_carbuncle.txt, 05_scandal_in_bohemia.txt | Chunks: {'03_blue_carbuncle.txt#4', '05_scandal_in_bohemia.txt#13', '01_red_headed_league.txt#11', '03_blue_carbuncle.txt#3', '03_blue_carbuncle.txt#12'}
      Expected: None | Expected chunks: None
      Facts matched: 0/3
      Latency: 0.8151580069970805s
      Answer: The excerpts provided do not contain any information about Professor Moriarty or a ransom for stolen crown jewels in Berkshire. Therefore, I cannot answer your question.
      Expected ans: ['Not present in text', 'No Moriarty mention', 'No crown jewels mention']

  Source-match: 9/10
  Chunk-match 8/10

## ========================================================================================== ##
