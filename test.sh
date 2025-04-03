for file in `ls ../*parta*`
do
	fileName=`basename $file`
	mv $file .
	git lfs track $fileName
	git add $fileName
	git commit -m "Add part"
	git push

done
