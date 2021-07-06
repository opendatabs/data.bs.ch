## Updating the reuse page
The goal is to have all the information about the reuses available on https://data.bs.ch/pages/reuses/.
Currently, after registering the reuse, the attributes "reuse_category" and "creator_category" are not automatically provided. They must be added manually to a file by following these steps:

1. Download the latest file
	- Download the file reuse-categories.xls (or csv, depending on the format) in the back office under https://data.bs.ch/backoffice/catalog/datasets/reuses-categories/#sources.
2. Add the attributes
	- download the dataset from https://data.bs.ch/explore/dataset/100080/
	- copy the "title" and the "dataset_id" from the downloaded data set
	- add the missing attributes "reuse_category" and "creator_category"
	- add in "created_at_join" the values given in "dateforjoinclean". This value, as well as "dataset_id" serve as identifiers.

3. Upload the file again, save and publish

The "Weiterverwendungen von OGD Datensätzen" dataset under https://data.bs.ch/explore/dataset/100080/ is updated hourly - on https://data.bs.ch/pages/reuses/ the reuse category and also the creator category should be visible no later than then.

Liebe Gruess,
Boris Djakovic