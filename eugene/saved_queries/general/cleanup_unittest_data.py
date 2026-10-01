
  

  
  
labels = [
  "activity",                         
  "agreement",
  "biologicalphenomenon",
  "biologicalentity",                      
  "capability",                       
  "celestialbody",                    
  "challenge",                        
  "city",                             
  "concept",                          
  "continent",                        
  "country",                          
  "countrygroup",                     
  "criminalactivity",                 
  "domain",                           
  "economicactivity",                 
  "economicandsocialactivity",        
  "economicinitiative",               
  "entity",                           
  "environmentalactivity",            
  "environmentalissue",               
  "ethnic_group",                     
  "event",                            
  "geographicalregion",               
  "geopoliticalboundary",             
  "geopoliticalentity",               
  "geopoliticalissue",                
  "globalhealthissue",                
  "globalissue",                      
  "government",                       
  "governmentagency",                 
  "governmentbody",                   
  "governmententity",                 
  "governmentpersonnel",              
  "group",                            
  "groupofcountries",                 
  "healthinitiative",                 
  "healthissue",                      
  "humanchallenge",                   
  "infrastructure",                   
  "internationalagreement",           
  "legislation",                      
  "location",                         
  "material",                         
  "militantgroup",                    
  "militaryasset",                    
  "militarycapability",               
  "militaryorganization",             
  "militarystrategy",                 
  "nationalsecurity",                 
  "organization",                     
  "person",                           
  "politicalandmilitaryorganization", 
  "politicalentity",                  
  "politicalissue",                   
  "politicalorganization",            
  "product",                          
  "program",                          
  "region",                           
  "role",                             
  "securityissue",                    
  "securitythreat",                   
  "socialissue",                      
  "socialphenomenon",                 
  "strategy",                         
  "substance",                        
  "technologicalconcept",             
  "technologicalissue",               
  "technology",                       
  "territory",                        
  "terroristorganization"    
  "threat",                           
  "tool",                             
  "unknown",                          
  "virus",                            
  "weapon",                           
  "weaponsystem"
]


for label in labels:
  cypher=f"""
    match (n1:{label})-[r]-(n2)
    delete r, n1;
  """
  print(cypher)
  delete_node=f"""
    match (n1:{label})
    delete n1;
  """
  print(delete_node)