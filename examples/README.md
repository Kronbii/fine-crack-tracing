# Examples

Two walls from the [Concrete Crack Segmentation Dataset](https://data.mendeley.com/datasets/jwsn7tfbrp/1) by Çağlar Fırat Özgenel (Mendeley Data, 2019), licensed [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The photos were taken in buildings at Middle East Technical University.

Changes from the originals: renamed (`609.jpg` is `wall-609`, `120.jpg` is `wall-120`), resized to half their width and height, and the masks thresholded to black and white and saved as PNG.

```bash
fine-tracing trace examples/masks --photos examples/photos -o results/examples
```
