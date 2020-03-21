# DXF Importer
A utility for Fusion 360 to import multiple DXF files.

[How to install](#How-to-install)  
[How to use](#How-to-use)   
[For Developers](#For-Developers)

----

###How to install<a name="How-to-install"></a>
1. [Download the latest distribution](https://github.com/tapnair/DXFImporter/tree/master/dist/DXFImporter-1.0.0.zip)


![](/resources/download.png)

2. Unzip the archive to a permanent location on your computer

###Fusion 360  

1. Launch Fusion 360.
2. On the main toolbar click the **Scripts and Addins** button in the **Addins** Pane

	![](/resources/scripts-addins_button.png)

3. Select the **Addins tab** and click the "add"  

    ![](/resources/scripts-addins.png)
    
4. Browse to the 'Project-Archiver' sub directory in the unzipped directory
    
     ![](/resources/unzipped.png)
     
5. Click run.  
6. Dismiss the Addins dialog.  
7.  Click the ProjectArchiver Tab and you should see **Archive** Panel and command.

	![](/resources/button.png)

----

###How to use<a name="How-to-use"></a>

Click the *DXF Import* button in toolbar.

You will be prompted to select the files you want to import.

![](/resources/dialog.png)

One component is created for each imported file.  One sketch is created for each layer in the DXF file.

On initial import the utility will spaces the DXF's in a grid.  You can set the spacing between the imported files by changing the value: *Spacing between parts.*

You can also adjust the number of files per row by adjusting the *Number per row* option.

Checking the *Reset Origins* option will move the entities in each sketch (layer of the dxf file) such that the bottom left corner of their bounding box is at the parts origin.

Checking the *Extrude Profiles* option with extrude (all profiles) of each sketch to the value specified by *Thickness.*

Click **OK**.

Fusion will import each DXF file. 

### For Developers<a name="For-Developers"></a>
Clone the repo

Update the apper submodule by browsing to the 'Project-Archiver' sub directory in the unzipped directory and executing:

    git submodule add https://github.com/tapnair/apper
   
## License
Samples are licensed under the terms of the [MIT License](http://opensource.org/licenses/MIT). Please see the [LICENSE](LICENSE) file for full details.

## Written by

Written by [Patrick Rainsberry](https://twitter.com/prrainsberry) <br /> (Autodesk Fusion 360 Product Manager)

See more useful [Fusion 360 Utilities](https://tapnair.github.io/index.html)


Analytics
[![Analytics](https://ga-beacon.appspot.com/UA-41076924-3/dxf-importer)](https://github.com/igrigorik/ga-beacon)



