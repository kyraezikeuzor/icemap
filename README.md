# icemap

we strongly believe that the American people should have full insight into the actions of its democratically-elected government.

icemap.dev aims to educate the American people on the activities and injustices of America's Immigration Customs Agency (ICE),
with specific focus on its Enforcement and Removal Operations department.

icemap aggregates both unstructured and structured data from a multitude of sources, consolidating this signal into useful
information for the American people.

icemap does not aim to hinder operations nor spark fear, but instead provide a lens with which the American people can
observe their government. 

our realization is that transparency, not abstract political messaging, will best inform the American public.

in line with our principles of transparency, icemap is fully open-source and available under the MIT license.

todo:
 - scraper currently store information locally in csv files. adapt the programs to instead make api requests to progressively update a live database. use aws lambda to ensure that the pipeline is robust, live, w/o wasted compute and time. verifies "new" articles against the existing database.
 - use deepseek to interpret and best structure textual data
 - frontend