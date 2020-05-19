# DXF Importer
A utility for Fusion 360 to import multiple DXF files.

[How to install](#How-to-install)  
[How to use](#How-to-use)   
[For Developers](#For-Developers)

----

## How to install<a name="How-to-install"></a>
1. [Find the latest distribution](https://github.com/tapnair/DXFImporter/tree/master/dist/)

![](/resources/dist.png)

2. Navigate to the file in github and select download. _(Note right-click "save target as" / "save link as" won't work)

![](/resources/download.png)

3. Unzip the archive to a permanent location on your computer

![](/resources/unzipped.png)

### Inside Fusion 360  

1. Launch Fusion 360.
2. On the main toolbar click the **Scripts and Addins** button in the **Addins** Pane

	![](/resources/scripts-addins_button.png)

3. Select the **Addins tab** and click the "add"  

    ![](/resources/scripts-addins.png)
    
4. Browse to the 'DXFImporter' sub directory in the unzipped directory
*Note: this may be the top level folder depending on the zip utility you use or if it is mac vs. windows.*
    
     ![](/resources/unzipped.png)
     
5. Click run.  
6. Dismiss the Addins dialog.  
7.  Click the DXFImporter Tab and you should see **DXF Import** Panel and command.

	![](/resources/button.png)

----

### How to use<a name="How-to-use"></a>

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

Update the apper submodule by browsing to the unzipped directory and executing:

    git submodule update --remote
   
## License
Copyright 2020 Patrick Rainsberry

Licensed under the Apache License, Version 2.0 (the “License”); you may not use this file except in compliance with the License.

You may obtain a copy of the License at:

[http://www.apache.org/licenses/LICENSE-2.0](http://www.apache.org/licenses/LICENSE-2.0)

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an “AS IS” BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.

## Written by

Written by [Patrick Rainsberry](https://twitter.com/prrainsberry) <br /> (Autodesk Fusion 360 Product Manager)

See more useful [Fusion 360 Utilities](https://tapnair.github.io/index.html)


Analytics
[![Analytics](https://ga-beacon.appspot.com/UA-41076924-3/dxf-importer)](https://github.com/igrigorik/ga-beacon)



